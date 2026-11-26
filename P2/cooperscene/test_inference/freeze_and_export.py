"""Freeze the validation protocol, check it, then export the test split.

The score, radius, spacing, and grid centers come from the validation run.
Nothing in this file is adjusted from test detections.
"""

import hashlib
import importlib.util
import json
import os
import sys
import time
import traceback

import numpy as np

DATA_ROOT = "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/data/mini/mini"
REPO = "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/src/CooperScene"
CFG = os.path.join(REPO, "assets/bevfusion/bevfusion_single_lidar.py")
CKPT = os.path.join(REPO, "assets/bevfusion/bevfusion_single_lidar.pth")
CONVERTER = os.path.join(REPO, "tools/dataset_converters/data_converter.py")
VALIDATION_DIR = "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/validation_inference"
OUT = os.environ.get(
    "TEST_OUT",
    "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/test_inference",
)
EXPECTED_SHA256 = "d71292a772a3f422eb818ab5012a893ee325bffef572524f9c89681eea50f761"
AGENTS = ("1", "2", "3")
SCORE = 0.10
RADIUS = 7.5
SPACING = 15.0
ORIGIN = (-75.0, -105.0)
WINDOW = 72.0
EGO_RADIUS = 3.0
EGO_REMOVAL_CAP = 0.10
RUN_IDS = {
    "1": "bevfusion_single_lidar_test_vehicle1",
    "2": "bevfusion_single_lidar_test_vehicle2",
    "3": "bevfusion_single_lidar_test_vehicle3",
}
# Hypothetical simulator interval from examples/f0/three_agent_f0.json.
# It is not a measured CooperScene frame period.
INTERVAL_MS = 300.0


def load_converter():
    spec = importlib.util.spec_from_file_location("cs_data_converter", CONVERTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path, expected_split):
    rows = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("split") != expected_split:
                raise SystemExit(f"SPLIT_MISMATCH {path} {record.get('split')}")
            if str(record.get("vehicle_id")) not in AGENTS:
                raise SystemExit(f"UNEXPECTED_VEHICLE {path} {record.get('vehicle_id')}")
            rows[str(record["timestamp"])] = record
    return rows


def frozen_grid():
    with open(os.path.join(VALIDATION_DIR, "summary.json"), "r", encoding="utf-8") as handle:
        summary = json.load(handle)
    recommendation = summary["recommendation"]
    grid = recommendation["grid"]
    centers = grid.get("centers_xy_m")
    origin = grid.get("origin_xy_m")
    problems = []
    if abs(float(recommendation["score_threshold"]) - SCORE) > 1e-9:
        problems.append("score")
    if abs(float(grid["radius_m"]) - RADIUS) > 1e-9:
        problems.append("radius")
    if abs(float(grid["spacing_m"]) - SPACING) > 1e-9:
        problems.append("spacing")
    if origin is None or abs(float(origin[0]) - ORIGIN[0]) > 1e-6 or abs(float(origin[1]) - ORIGIN[1]) > 1e-6:
        problems.append("origin")
    if not isinstance(centers, list) or len(centers) != 144:
        problems.append("center_count")
    if problems:
        raise SystemExit("FROZEN_GRID_MISMATCH " + ",".join(problems))
    return [[float(point[0]), float(point[1])] for point in centers]


def in_window(center, pose, rotation_fn):
    rotation = rotation_fn(pose[3], pose[4], pose[5])
    delta = np.array([center[0] - pose[0], center[1] - pose[1], 0.0], dtype=np.float64)
    ego = rotation.T @ delta
    return abs(float(ego[0])) <= WINDOW and abs(float(ego[1])) <= WINDOW


def near_ego(point, pose):
    return (point[0] - pose[0]) ** 2 + (point[1] - pose[1]) ** 2 <= EGO_RADIUS ** 2


def kept_centers(record, key):
    pose = record["ego_pose"]
    kept = []
    removed = 0
    total = 0
    for box, score in zip(record[key], record["scores"] if key.startswith("pred") else [None] * len(record[key])):
        total += 1
        if key.startswith("pred") and float(score) < SCORE:
            continue
        if near_ego(box, pose):
            removed += 1
            continue
        kept.append((float(box[0]), float(box[1])))
    return kept, removed, total


def region_hit(centers, circle):
    limit = RADIUS ** 2
    for point in centers:
        if (point[0] - circle[0]) ** 2 + (point[1] - circle[1]) ** 2 <= limit:
            return 1
    return 0


def common_roi_indices(records, circles, rotation_fn):
    chosen = []
    for index, circle in enumerate(circles):
        if all(in_window(circle, records[agent]["ego_pose"], rotation_fn) for agent in AGENTS):
            chosen.append(index)
    return chosen


def blank_region():
    return {"tp": 0, "fp": 0, "fn": 0, "tn": 0}


def add_region(counts, prediction, truth):
    if prediction == 1 and truth == 1:
        counts["tp"] += 1
    elif prediction == 1 and truth == 0:
        counts["fp"] += 1
    elif prediction == 0 and truth == 1:
        counts["fn"] += 1
    else:
        counts["tn"] += 1


def region_q(counts):
    total = counts["tp"] + counts["fp"] + counts["fn"] + counts["tn"]
    if total == 0:
        return None
    return (counts["fp"] + counts["fn"]) / total


def check_protocol(converter, circles):
    validation = {
        agent: load_jsonl(os.path.join(VALIDATION_DIR, f"vehicle_{agent}.jsonl"), "validate")
        for agent in AGENTS
    }
    timestamps = [set(validation[agent]) for agent in AGENTS]
    if not timestamps[0] or timestamps[0] != timestamps[1] or timestamps[1] != timestamps[2]:
        raise SystemExit("VALIDATION_TIMESTAMPS_NOT_SHARED")
    ordered = sorted(timestamps[0])
    ego_boxes = {agent: {"removed": 0, "annotated": 0} for agent in AGENTS}
    ego_preds = {agent: {"removed": 0, "above_score": 0} for agent in AGENTS}
    distances = []
    region = {agent: blank_region() for agent in AGENTS}
    disagreement = 0
    decisions = 0
    common_counts = []
    positive_truth = 0
    for timestamp in ordered:
        records = {agent: validation[agent][timestamp] for agent in AGENTS}
        per_gt = {}
        per_pred = {}
        for agent, record in records.items():
            gt, removed, annotated = kept_centers(record, "gt_boxes_world")
            pred, pred_removed, _total = kept_centers(record, "pred_boxes_world")
            per_gt[agent] = gt
            per_pred[agent] = pred
            ego_boxes[agent]["removed"] += removed
            ego_boxes[agent]["annotated"] += annotated
            above = sum(float(score) >= SCORE for score in record["scores"])
            ego_preds[agent]["removed"] += pred_removed
            ego_preds[agent]["above_score"] += above
            pose = record["ego_pose"]
            for box in record["gt_boxes_world"]:
                distances.append(float(np.hypot(box[0] - pose[0], box[1] - pose[1])))
        indices = common_roi_indices(records, circles, converter.get_rotation_matrix)
        common_counts.append(len(indices))
        union = [point for agent in AGENTS for point in per_gt[agent]]
        for index in indices:
            circle = circles[index]
            truth = region_hit(union, circle)
            positive_truth += truth
            decisions += 1
            single = [region_hit(per_gt[agent], circle) for agent in AGENTS]
            if any(value != truth for value in single):
                disagreement += 1
            for agent in AGENTS:
                add_region(region[agent], region_hit(per_pred[agent], circle), truth)
    reasons = []
    for agent in AGENTS:
        annotated = ego_boxes[agent]["annotated"]
        fraction = ego_boxes[agent]["removed"] / annotated if annotated else 0.0
        ego_boxes[agent]["fraction"] = fraction
        if fraction > EGO_REMOVAL_CAP:
            reasons.append(f"ego_gt_{agent}")
        above = ego_preds[agent]["above_score"]
        pred_fraction = ego_preds[agent]["removed"] / above if above else 0.0
        ego_preds[agent]["fraction"] = pred_fraction
        if pred_fraction > EGO_REMOVAL_CAP:
            reasons.append(f"ego_pred_{agent}")
    if any(count == 0 for count in common_counts):
        reasons.append("frame_without_common_roi")
    rates = {}
    for agent in AGENTS:
        q = region_q(region[agent])
        rates[agent] = {"q": q, **region[agent], "n": sum(region[agent].values())}
        if q is None or not (0.0 < q < 0.5):
            rates[agent]["importer_range"] = False
        else:
            rates[agent]["importer_range"] = True
    report = {
        "validation_frames": len(ordered),
        "ego_gt": ego_boxes,
        "ego_predictions_at_or_above_score": ego_preds,
        "gt_distance_to_own_lidar_m": {
            "min": float(min(distances)) if distances else None,
            "median": float(np.median(distances)) if distances else None,
            "p10": float(np.percentile(distances, 10)) if distances else None,
        },
        "common_rois_per_frame": {
            "min": int(min(common_counts)) if common_counts else 0,
            "median": float(np.median(common_counts)) if common_counts else 0,
            "max": int(max(common_counts)) if common_counts else 0,
        },
        "label_disagreement_rate": disagreement / decisions if decisions else None,
        "label_disagreements": disagreement,
        "common_decisions": decisions,
        "positive_truth_regions": positive_truth,
        "region_error": rates,
        "gate_failures": reasons,
        "passed": not reasons,
    }
    return report, validation


def list_frames(agent):
    split_dir = os.path.join(DATA_ROOT, "test")
    frames = []
    for scenario in sorted(os.listdir(split_dir)):
        agent_dir = os.path.join(split_dir, scenario, agent)
        if not os.path.isdir(agent_dir):
            continue
        for name in sorted(os.listdir(agent_dir)):
            if not name.endswith(".pcd"):
                continue
            stem = name[:-4]
            yaml_path = os.path.join(agent_dir, stem + ".yaml")
            if not os.path.isfile(yaml_path):
                continue
            if stem.startswith("data_protocol") or stem.endswith("_additional") or stem.endswith("_separate"):
                continue
            frames.append(
                {
                    "scenario": scenario,
                    "timestamp": stem,
                    "pcd": os.path.join(agent_dir, name),
                    "yaml": yaml_path,
                }
            )
    return frames


def load_yaml(path):
    import yaml

    with open(path, "r", encoding="utf-8") as handle:
        return yaml.unsafe_load(handle)


def as_pose(meta):
    pose = meta.get("lidar_pose", meta.get("true_ego_pos"))
    if pose is None:
        return None
    values = [float(v) for v in list(pose)[:6]]
    return values if len(values) == 6 else None


def world_box_from_yaml(converter, veh):
    loc = np.asarray(veh["location"], dtype=np.float64)
    extent = veh["extent"]
    angle = veh["angle"]
    center = np.asarray(veh.get("center", [0, 0, 0]), dtype=np.float64)
    rotation = converter.get_rotation_matrix(float(angle[0]), float(angle[1]), float(angle[2]))
    center_world = rotation @ center
    return [
        float(loc[0] + center_world[0]),
        float(loc[1] + center_world[1]),
        float(loc[2] + center_world[2]),
        float(extent[0]) * 2.0,
        float(extent[1]) * 2.0,
        float(extent[2]) * 2.0,
        float(np.radians(float(angle[1]))),
    ]


def ego_box_to_world(converter, box, pose):
    rotation = converter.get_rotation_matrix(pose[3], pose[4], pose[5])
    pos = rotation @ np.asarray(box[:3], dtype=np.float64) + np.asarray(pose[:3], dtype=np.float64)
    yaw = float(box[6]) + float(np.radians(pose[4]))
    yaw = float((yaw + np.pi) % (2.0 * np.pi) - np.pi)
    return [float(pos[0]), float(pos[1]), float(pos[2]), float(box[3]), float(box[4]), float(box[5]), yaw]


def find_instances(obj, depth=0):
    if obj is None or depth > 5:
        return None
    if hasattr(obj, "pred_instances_3d"):
        inst = obj.pred_instances_3d
        if inst is not None and hasattr(inst, "scores_3d"):
            return inst
    if isinstance(obj, (list, tuple)):
        for item in obj:
            found = find_instances(item, depth + 1)
            if found is not None:
                return found
    if isinstance(obj, dict):
        for item in obj.values():
            found = find_instances(item, depth + 1)
            if found is not None:
                return found
    return None


def load_model():
    import torch
    from mmdet3d.apis import init_model

    original = torch.load

    def trusted(*args, **kwargs):
        kwargs["weights_only"] = False
        return original(*args, **kwargs)

    torch.load = trusted
    model = init_model(CFG, None, device="cuda:0")
    blob = torch.load(CKPT, map_location="cpu")
    state = blob.get("state_dict", blob)
    own = model.state_dict()
    fixed = {}
    permuted = 0
    bad = []
    for key, value in state.items():
        target = key[7:] if key.startswith("module.") else key
        if target not in own:
            bad.append(target)
            continue
        want = tuple(own[target].shape)
        if tuple(value.shape) == want:
            fixed[target] = value
        elif getattr(value, "ndim", 0) == 5 and tuple(value.permute(1, 2, 3, 4, 0).shape) == want:
            fixed[target] = value.permute(1, 2, 3, 4, 0).contiguous()
            permuted += 1
        else:
            bad.append(target)
    missing, unexpected = model.load_state_dict(fixed, strict=False)
    if bad or missing or unexpected or permuted != 21:
        raise SystemExit(
            f"WEIGHT_LOAD_INCOMPLETE permuted {permuted} bad {len(bad)} missing {len(missing)} unexpected {len(unexpected)}"
        )
    model.eval()
    return model


def infer(model, bin_path):
    import torch
    from mmdet3d.apis import inference_detector

    torch.cuda.synchronize()
    start = time.perf_counter()
    result = inference_detector(model, bin_path)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    instances = find_instances(result)
    if instances is None:
        raise RuntimeError("NO_PRED_INSTANCES")
    scores = instances.scores_3d.detach().cpu().numpy().astype(np.float64)
    tensor = instances.bboxes_3d
    tensor = tensor.tensor if hasattr(tensor, "tensor") else tensor
    boxes = tensor.detach().cpu().numpy().astype(np.float64)[:, :7]
    peak = int(torch.cuda.max_memory_allocated())
    return boxes, scores, elapsed, peak


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def importer_manifest(rates):
    files = {
        "1": "vehicle_1_predictions.jsonl",
        "2": "vehicle_2_predictions.jsonl",
        "3": "vehicle_3_predictions.jsonl",
    }
    manifest = {
        "dataset": "CooperScene",
        "split": "test",
        "vehicle_ids": ["1", "2", "3"],
        "roi_protocol": "predeclared_world_xy_grid_v1",
        "coordinate_frame": "cooperscene_global_xy_m",
        "prediction_origin": "real_detector_export",
        "physical_detector_runs": RUN_IDS,
        "assumed_source_error": {agent: rates[agent]["q"] for agent in AGENTS},
        "error_estimator_status": "unfitted_assumption",
        "error_rate_note": (
            "assumed_source_error values are binary region-mismatch rates measured on the "
            "validation common ROIs. They are not object-level F1. The importer's fitted "
            "status is legal only for a train split, and this study did not fit on train."
        ),
        "interval_ms": INTERVAL_MS,
        "interval_note": "Hypothetical arrival interval from examples/f0/three_agent_f0.json, not measured here.",
        "checkpoint_sha256": {agent: EXPECTED_SHA256 for agent in AGENTS},
        "per_vehicle_prediction_exports": {
            agent: {"path": files[agent], "sha256": sha256_file(os.path.join(OUT, files[agent]))}
            for agent in AGENTS
        },
        "ground_truth_export": {
            "path": "ground_truth.jsonl",
            "sha256": sha256_file(os.path.join(OUT, "ground_truth.jsonl")),
        },
        "validation_region_error": rates,
    }
    path = os.path.join(OUT, "manifest.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    return path


def main():
    os.makedirs(OUT, exist_ok=True)
    converter = load_converter()
    circles = frozen_grid()
    protocol, _validation = check_protocol(converter, circles)
    with open(os.path.join(OUT, "protocol_check.json"), "w", encoding="utf-8") as handle:
        json.dump(protocol, handle, indent=2)
        handle.write("\n")
    print("PROTOCOL_COMMON_ROI", json.dumps(protocol["common_rois_per_frame"]), flush=True)
    print("PROTOCOL_EGO_GT", json.dumps(protocol["ego_gt"]), flush=True)
    print("PROTOCOL_LABEL_DISAGREEMENT", protocol["label_disagreement_rate"], flush=True)
    for agent in AGENTS:
        row = protocol["region_error"][agent]
        print(
            f"Q_REGION vehicle {agent} q {row['q']} n {row['n']} "
            f"tp {row['tp']} fp {row['fp']} fn {row['fn']} tn {row['tn']} "
            f"importer_range {row['importer_range']}",
            flush=True,
        )
    if not protocol["passed"]:
        print("PROTOCOL_GATE_FAILED", ",".join(protocol["gate_failures"]), flush=True)
        print("TEST_INFERENCE_NOT_STARTED", flush=True)
        sys.exit(2)
    print("PROTOCOL_GATE_PASSED", flush=True)

    frames = {agent: list_frames(agent) for agent in AGENTS}
    by_time = {}
    for agent, items in frames.items():
        print(f"COUNT test vehicle {agent} {len(items)}", flush=True)
        if len(items) != 30:
            raise SystemExit(f"TEST_FRAME_COUNT {agent} {len(items)}")
        for item in items:
            by_time.setdefault(item["timestamp"], {})[agent] = item
    if any(set(item) != set(AGENTS) for item in by_time.values()) or len(by_time) != 30:
        raise SystemExit("TEST_TIMESTAMPS_NOT_SHARED")

    if sha256_file(CKPT) != EXPECTED_SHA256:
        raise SystemExit("SHA256_MISMATCH")
    model = load_model()
    work_bin = os.path.join(OUT, "_work.bin")
    detections = {agent: {} for agent in AGENTS}
    times = {agent: [] for agent in AGENTS}
    peaks = []
    for timestamp in sorted(by_time):
        items = by_time[timestamp]
        scenarios = {items[agent]["scenario"] for agent in AGENTS}
        if len(scenarios) != 1:
            raise SystemExit(f"SCENARIO_MISMATCH {timestamp}")
        for agent in AGENTS:
            item = items[agent]
            meta = load_yaml(item["yaml"])
            pose = as_pose(meta)
            if pose is None:
                raise SystemExit(f"NO_POSE {agent} {timestamp}")
            if not converter.convert_pcd_to_bin(item["pcd"], work_bin):
                raise SystemExit(f"OFFICIAL_CONVERT_FAILED {item['pcd']}")
            boxes, scores, elapsed, peak = infer(model, work_bin)
            gt_world = []
            vehicles = meta.get("vehicles") or {}
            if isinstance(vehicles, dict):
                for veh in vehicles.values():
                    gt_world.append(world_box_from_yaml(converter, veh))
            pred_world = [ego_box_to_world(converter, box, pose) for box in boxes]
            record = {
                "split": "test",
                "scenario": item["scenario"],
                "timestamp": timestamp,
                "vehicle_id": agent,
                "run_id": RUN_IDS[agent],
                "lidar_path": item["pcd"],
                "ego_pose": pose,
                "gt_boxes_world": gt_world,
                "pred_boxes_world": pred_world,
                "scores": [float(value) for value in scores],
                "inference_seconds": elapsed,
                "checkpoint_sha256": EXPECTED_SHA256,
            }
            detections[agent][timestamp] = record
            times[agent].append(elapsed)
            peaks.append(peak)
            print(
                f"TEST vehicle {agent} {timestamp} {elapsed:.3f}s gt {len(gt_world)} max {float(scores.max()) if len(scores) else 0:.3f}",
                flush=True,
            )
    if os.path.exists(work_bin):
        os.remove(work_bin)
    for agent in AGENTS:
        write_jsonl(
            os.path.join(OUT, f"test_boxes_vehicle_{agent}.jsonl"),
            [detections[agent][timestamp] for timestamp in sorted(detections[agent])],
        )

    per_vehicle_rows = {agent: [] for agent in AGENTS}
    truth_rows = []
    merged_rows = []
    test_region = {agent: blank_region() for agent in AGENTS}
    for timestamp in sorted(by_time):
        records = {agent: detections[agent][timestamp] for agent in AGENTS}
        indices = common_roi_indices(records, circles, converter.get_rotation_matrix)
        per_pred = {}
        per_gt = {}
        for agent, record in records.items():
            pred, _removed, _total = kept_centers(record, "pred_boxes_world")
            gt, _removed_gt, _annotated = kept_centers(record, "gt_boxes_world")
            per_pred[agent] = pred
            per_gt[agent] = gt
        union = [point for agent in AGENTS for point in per_gt[agent]]
        take_id = str(records["1"]["scenario"])
        if any(token in take_id or token in timestamp for token in ("/", ":")):
            raise SystemExit(f"BAD_IDENTITY {take_id} {timestamp}")
        for index in indices:
            circle = circles[index]
            roi_id = f"grid_{index:03d}"
            truth = region_hit(union, circle)
            predictions = {agent: region_hit(per_pred[agent], circle) for agent in AGENTS}
            for agent in AGENTS:
                add_region(test_region[agent], predictions[agent], truth)
                per_vehicle_rows[agent].append(
                    {
                        "take_id": take_id,
                        "frame_token": timestamp,
                        "roi_id": roi_id,
                        "vehicle_id": agent,
                        "prediction": predictions[agent],
                    }
                )
            truth_rows.append(
                {"take_id": take_id, "frame_token": timestamp, "roi_id": roi_id, "truth": truth}
            )
            merged_rows.append(
                {
                    "split": "test",
                    "take_id": take_id,
                    "frame_token": timestamp,
                    "roi_id": roi_id,
                    "truth": truth,
                    "predictions": predictions,
                    "roi": {
                        "frame": "cooperscene_global_xy_m",
                        "center_xy_m": circle,
                        "radius_m": RADIUS,
                    },
                }
            )
    for agent in AGENTS:
        write_jsonl(os.path.join(OUT, f"vehicle_{agent}_predictions.jsonl"), per_vehicle_rows[agent])
    write_jsonl(os.path.join(OUT, "ground_truth.jsonl"), truth_rows)
    write_jsonl(os.path.join(OUT, "predictions.jsonl"), merged_rows)
    importer_manifest(protocol["region_error"])
    print(f"EXPORTED_ROWS {len(merged_rows)}", flush=True)
    for agent in AGENTS:
        row = test_region[agent]
        print(
            f"TEST_REGION_ERROR_NOT_USED_FOR_PROTOCOL vehicle {agent} q {region_q(row)} "
            f"n {sum(row.values())} tp {row['tp']} fp {row['fp']} fn {row['fn']} tn {row['tn']}",
            flush=True,
        )
        print(
            f"TIMING test vehicle {agent} n {len(times[agent])} mean_s {float(np.mean(times[agent])):.6f} "
            f"median_s {float(np.median(times[agent])):.6f}",
            flush=True,
        )
    print(f"PEAK_ALLOCATED_MIB {max(peaks) / 1024**2:.2f}", flush=True)
    print("TEST_INFERENCE_DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("TEST_INFERENCE_FAILED")
        sys.exit(1)
