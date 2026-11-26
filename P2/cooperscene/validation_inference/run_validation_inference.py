"""Validation-split inference for CooperScene vehicles 1, 2, and 3.

Uses the official PCD intensity conversion (divide by 65535). Does not read
the test split, does not train, and does not load agent 0.
"""

import csv
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
OUT = os.environ.get(
    "VALIDATION_OUT",
    "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/validation_inference",
)
EXPECTED_SHA256 = "d71292a772a3f422eb818ab5012a893ee325bffef572524f9c89681eea50f761"
SPLIT = "validate"
AGENTS = ("1", "2", "3")
SCORE_THRESHOLDS = (0.05, 0.1, 0.3, 0.5)
IOU_THRESHOLDS = (0.50, 0.70)
LOWEST_SCORE = min(SCORE_THRESHOLDS)


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


def list_frames(root, agent):
    split_dir = os.path.join(root, SPLIT)
    if not os.path.isdir(split_dir):
        raise SystemExit(f"NO_VALIDATION_SPLIT {split_dir}")
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
                    "agent": agent,
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
    if len(values) != 6:
        return None
    return values


def world_box_from_yaml(converter, veh):
    loc = np.asarray(veh["location"], dtype=np.float64)
    extent = veh["extent"]
    angle = veh["angle"]
    center = np.asarray(veh.get("center", [0, 0, 0]), dtype=np.float64)
    rotation = converter.get_rotation_matrix(float(angle[0]), float(angle[1]), float(angle[2]))
    center_world = rotation @ center
    yaw = float(np.radians(float(angle[1])))
    return [
        float(loc[0] + center_world[0]),
        float(loc[1] + center_world[1]),
        float(loc[2] + center_world[2]),
        float(extent[0]) * 2.0,
        float(extent[1]) * 2.0,
        float(extent[2]) * 2.0,
        yaw,
    ]


def ego_box_to_world(converter, box, pose):
    rotation = converter.get_rotation_matrix(pose[3], pose[4], pose[5])
    pos = rotation @ np.asarray(box[:3], dtype=np.float64)
    pos = pos + np.asarray(pose[:3], dtype=np.float64)
    yaw = float(box[6]) + float(np.radians(pose[4]))
    yaw = float((yaw + np.pi) % (2.0 * np.pi) - np.pi)
    return [float(pos[0]), float(pos[1]), float(pos[2]), float(box[3]), float(box[4]), float(box[5]), yaw]


def rows(boxes):
    if len(boxes) == 0:
        return []
    return [[float(v) for v in box[:7]] for box in np.asarray(boxes, dtype=np.float64)]


def bev_corners(box):
    x, y, dx, dy, yaw = box[0], box[1], box[3], box[4], box[6]
    c, s = np.cos(yaw), np.sin(yaw)
    half_l, half_w = dx / 2.0, dy / 2.0
    local = np.array(
        [[half_l, half_w], [half_l, -half_w], [-half_l, -half_w], [-half_l, half_w]],
        dtype=np.float64,
    )
    rotation = np.array([[c, -s], [s, c]], dtype=np.float64)
    return local @ rotation.T + np.array([x, y], dtype=np.float64)


def bev_iou_matrix(predictions, ground_truth):
    from shapely.geometry import Polygon

    if len(predictions) == 0 or len(ground_truth) == 0:
        return np.zeros((len(predictions), len(ground_truth)), dtype=np.float64)
    pred_polys = []
    gt_polys = []
    for box in predictions:
        poly = Polygon(bev_corners(box))
        pred_polys.append(poly if poly.is_valid else poly.buffer(0))
    for box in ground_truth:
        poly = Polygon(bev_corners(box))
        gt_polys.append(poly if poly.is_valid else poly.buffer(0))
    ious = np.zeros((len(predictions), len(ground_truth)), dtype=np.float64)
    for i, pred in enumerate(pred_polys):
        for j, gt in enumerate(gt_polys):
            union = pred.union(gt).area
            if union <= 0:
                continue
            ious[i, j] = float(pred.intersection(gt).area / union)
    return ious


def one_to_one(ious, iou_threshold):
    n_pred, n_gt = ious.shape
    if n_pred == 0 or n_gt == 0:
        return 0
    from scipy.optimize import linear_sum_assignment

    cost = np.where(ious >= iou_threshold, -ious, 1.0e6)
    rows, cols = linear_sum_assignment(cost)
    return int(sum(ious[r, c] >= iou_threshold for r, c in zip(rows, cols)))


def count_matches(ious, scores, n_gt):
    counts = {}
    for score_thr in SCORE_THRESHOLDS:
        keep = scores >= score_thr
        n_pred = int(keep.sum())
        block = ious[keep] if n_pred else np.zeros((0, n_gt), dtype=np.float64)
        counts[f"{score_thr:g}"] = {}
        for iou_thr in IOU_THRESHOLDS:
            tp = one_to_one(block, iou_thr) if n_pred and n_gt else 0
            counts[f"{score_thr:g}"][f"{iou_thr:.2f}"] = {
                "tp": tp,
                "fp": n_pred - tp,
                "fn": n_gt - tp,
            }
    return counts


def add_counts(total, part):
    for score_thr, by_iou in part.items():
        for iou_thr, row in by_iou.items():
            dest = total[score_thr][iou_thr]
            dest["tp"] += row["tp"]
            dest["fp"] += row["fp"]
            dest["fn"] += row["fn"]


def blank_counts():
    return {
        f"{score:g}": {f"{iou:.2f}": {"tp": 0, "fp": 0, "fn": 0} for iou in IOU_THRESHOLDS}
        for score in SCORE_THRESHOLDS
    }


def rates(row):
    tp, fp, fn = row["tp"], row["fp"], row["fn"]
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    if precision is None or recall is None or (precision + recall) == 0:
        f1 = None if precision is None or recall is None else 0.0
    else:
        f1 = 2.0 * precision * recall / (precision + recall)
    return precision, recall, f1


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


def boxes_and_scores(instances):
    scores = instances.scores_3d.detach().cpu().numpy().astype(np.float64)
    tensor = instances.bboxes_3d
    tensor = tensor.tensor if hasattr(tensor, "tensor") else tensor
    return tensor.detach().cpu().numpy().astype(np.float64)[:, :7], scores


def load_model():
    import torch
    from mmdet3d.apis import init_model

    original = torch.load

    def trusted(*args, **kwargs):
        kwargs["weights_only"] = False
        return original(*args, **kwargs)

    torch.load = trusted
    torch.cuda.reset_peak_memory_stats()
    model = init_model(CFG, None, device="cuda:0")
    blob = torch.load(CKPT, map_location="cpu")
    state = blob.get("state_dict", blob)
    own = model.state_dict()
    fixed = {}
    permuted = 0
    mismatched = []
    absent = []
    for key, value in state.items():
        target = key[7:] if key.startswith("module.") else key
        if target not in own:
            absent.append(target)
            continue
        want = tuple(own[target].shape)
        if tuple(value.shape) == want:
            fixed[target] = value
        elif value.ndim == 5 and tuple(value.permute(1, 2, 3, 4, 0).shape) == want:
            fixed[target] = value.permute(1, 2, 3, 4, 0).contiguous()
            permuted += 1
        else:
            mismatched.append(target)
    missing, unexpected = model.load_state_dict(fixed, strict=False)
    model.eval()
    report = {
        "permuted": permuted,
        "still_mismatched": mismatched,
        "missing_keys": list(missing),
        "unexpected_keys": list(unexpected),
        "checkpoint_keys_absent_from_model": absent,
        "model_class": type(model).__name__,
    }
    if mismatched or missing or unexpected or absent:
        raise SystemExit("WEIGHT_LOAD_INCOMPLETE " + json.dumps(report))
    load_peak = int(torch.cuda.max_memory_allocated())
    torch.cuda.reset_peak_memory_stats()
    return model, report, load_peak


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
        raise RuntimeError(f"NO_PRED_INSTANCES {type(result).__name__}")
    boxes, scores = boxes_and_scores(instances)
    peak = int(torch.cuda.max_memory_allocated())
    return boxes, scores, elapsed, peak


def nearest_neighbor_distances(points_by_frame):
    distances = []
    for points in points_by_frame:
        if len(points) < 2:
            continue
        xy = np.asarray(points, dtype=np.float64)
        for i in range(len(xy)):
            delta = xy - xy[i]
            dist = np.hypot(delta[:, 0], delta[:, 1])
            dist[i] = np.inf
            distances.append(float(dist.min()))
    return distances


def recommend(pooled, world_gt, nn_distances):
    primary = []
    for score in SCORE_THRESHOLDS:
        precision, recall, f1 = rates(pooled[f"{score:g}"]["0.50"])
        primary.append(
            {
                "score_threshold": score,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "counts": pooled[f"{score:g}"]["0.50"],
            }
        )
    usable = [row for row in primary if row["f1"] is not None]
    if not usable:
        choice = None
        reason = "No validation frame produced both predictions and ground truth at IoU 0.50."
    else:
        best = max(row["f1"] for row in usable)
        tied = [row for row in usable if best - row["f1"] <= 0.01]
        choice = max(tied, key=lambda row: row["score_threshold"])
        reason = (
            "Highest pooled F1 at one-to-one BEV IoU 0.50. "
            "A cutoff within 0.01 F1 of the best loses to the higher cutoff. "
            "The 0.70 match is reported and is not used to choose the cutoff. "
            "The four cutoffs were fixed before this run."
        )
    xy = np.asarray(world_gt, dtype=np.float64) if world_gt else np.zeros((0, 2))
    radius = 7.5
    spacing = 15.0
    grid = {"radius_m": radius, "spacing_m": spacing, "frame": "cooperscene_global_xy_m"}
    if len(xy):
        span_x = float(xy[:, 0].max() - xy[:, 0].min())
        span_y = float(xy[:, 1].max() - xy[:, 1].min())
        grid["gt_span_m"] = [span_x, span_y]
        grid["gt_xy_min_m"] = [float(xy[:, 0].min()), float(xy[:, 1].min())]
        grid["gt_xy_max_m"] = [float(xy[:, 0].max()), float(xy[:, 1].max())]
        if span_x > 5000 or span_y > 5000:
            grid["centers_omitted"] = "validation ground truth spans more than 5 km"
        else:
            origin_x = float(np.floor((xy[:, 0].min() - radius) / spacing) * spacing)
            origin_y = float(np.floor((xy[:, 1].min() - radius) / spacing) * spacing)
            last_x = float(np.ceil((xy[:, 0].max() + radius) / spacing) * spacing)
            last_y = float(np.ceil((xy[:, 1].max() + radius) / spacing) * spacing)
            xs = np.arange(origin_x, last_x + spacing * 0.5, spacing)
            ys = np.arange(origin_y, last_y + spacing * 0.5, spacing)
            grid.update(
                {
                    "origin_xy_m": [origin_x, origin_y],
                    "nx": int(len(xs)),
                    "ny": int(len(ys)),
                    "n_circles": int(len(xs) * len(ys)),
                }
            )
            if len(xs) * len(ys) <= 5000:
                grid["centers_xy_m"] = [[float(x), float(y)] for x in xs for y in ys]
    nn = np.asarray(nn_distances, dtype=np.float64)
    nn_summary = None
    if len(nn):
        nn_summary = {
            "count": int(len(nn)),
            "median_m": float(np.median(nn)),
            "p10_m": float(np.percentile(nn, 10)),
        }
    same_circle = bool(nn_summary and nn_summary["median_m"] < spacing)
    return {
        "score_threshold": None if choice is None else choice["score_threshold"],
        "score_reason": reason,
        "f1_at_iou_0.50": primary,
        "grid": grid,
        "same_frame_gt_nearest_neighbor_m": nn_summary,
        "presence_circles_can_contain_multiple_vehicles": same_circle,
        "grid_reason": (
            "Radius 7.5 m is the radius already named for this study. "
            "It was not tuned on these boxes. Centers sit on a 15 m lattice, "
            "aligned to multiples of 15 m, covering every validation ground-truth "
            "center. A label is presence of a vehicle center inside the circle, "
            "not vehicle identity and not 3D IoU."
        ),
        "fit_split": "validate",
        "test_split_used": False,
    }


def write_metrics_csv(path, by_vehicle, pooled):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "vehicle_id",
                "score_threshold",
                "iou_threshold",
                "tp",
                "fp",
                "fn",
                "precision",
                "recall",
                "f1",
            ],
        )
        writer.writeheader()
        blocks = [(agent, by_vehicle[agent]) for agent in AGENTS]
        blocks.append(("all", pooled))
        for vehicle, block in blocks:
            for score in SCORE_THRESHOLDS:
                for iou in IOU_THRESHOLDS:
                    row = block[f"{score:g}"][f"{iou:.2f}"]
                    precision, recall, f1 = rates(row)
                    writer.writerow(
                        {
                            "vehicle_id": vehicle,
                            "score_threshold": score,
                            "iou_threshold": iou,
                            "tp": row["tp"],
                            "fp": row["fp"],
                            "fn": row["fn"],
                            "precision": "" if precision is None else f"{precision:.6f}",
                            "recall": "" if recall is None else f"{recall:.6f}",
                            "f1": "" if f1 is None else f"{f1:.6f}",
                        }
                    )


def metric_lines(by_vehicle, pooled):
    lines = ["METRICS_BEGIN"]
    blocks = [(agent, by_vehicle[agent]) for agent in AGENTS] + [("all", pooled)]
    for vehicle, block in blocks:
        for score in SCORE_THRESHOLDS:
            for iou in IOU_THRESHOLDS:
                row = block[f"{score:g}"][f"{iou:.2f}"]
                precision, recall, f1 = rates(row)
                def fmt(value):
                    return "na" if value is None else f"{value:.4f}"

                lines.append(
                    f"{vehicle} score {score:g} iou {iou:.2f} "
                    f"tp {row['tp']} fp {row['fp']} fn {row['fn']} "
                    f"P {fmt(precision)} R {fmt(recall)} F1 {fmt(f1)}"
                )
    lines.append("METRICS_END")
    return lines


def main():
    os.makedirs(OUT, exist_ok=True)
    if os.path.isdir(os.path.join(DATA_ROOT, "test")):
        pass
    frames = {agent: list_frames(DATA_ROOT, agent) for agent in AGENTS}
    for agent, items in frames.items():
        print(f"COUNT vehicle {agent} {len(items)}", flush=True)
        for item in items:
            if "/test/" in item["pcd"].replace("\\", "/"):
                raise SystemExit("REFUSING_TEST_PATH " + item["pcd"])
    converter = load_converter()
    digest = sha256_file(CKPT)
    if digest != EXPECTED_SHA256:
        raise SystemExit("SHA256_MISMATCH " + digest)
    model, weight_report, load_peak = load_model()
    print(
        f"WEIGHTS permuted {weight_report['permuted']} missing 0 unexpected 0 load_peak_mib {load_peak / 1024**2:.1f}",
        flush=True,
    )

    by_vehicle = {agent: blank_counts() for agent in AGENTS}
    pooled = blank_counts()
    timing = {}
    world_gt = []
    nn_points = []
    roundtrip_errors = []
    failures = []
    work_bin = os.path.join(OUT, "_work.bin")

    for agent in AGENTS:
        items = frames[agent]
        times = []
        peaks = []
        out_path = os.path.join(OUT, f"vehicle_{agent}.jsonl")
        with open(out_path, "w", encoding="utf-8") as handle:
            for index, item in enumerate(items, start=1):
                try:
                    meta = load_yaml(item["yaml"])
                    pose = as_pose(meta)
                    if pose is None:
                        raise RuntimeError("NO_POSE")
                    if not converter.convert_pcd_to_bin(item["pcd"], work_bin):
                        raise RuntimeError("OFFICIAL_CONVERT_FAILED")
                    gt_ego = []
                    gt_world = []
                    vehicles = meta.get("vehicles") or {}
                    if not isinstance(vehicles, dict):
                        vehicles = {}
                    for veh in vehicles.values():
                        ego = converter.parse_cooperscene_vehicle(veh, pose)
                        world = world_box_from_yaml(converter, veh)
                        if ego is None:
                            continue
                        gt_ego.append(ego)
                        gt_world.append(world)
                        back = ego_box_to_world(converter, ego, pose)
                        roundtrip_errors.append(float(np.max(np.abs(np.asarray(back[:3]) - np.asarray(world[:3])))))
                    gt_ego_arr = np.asarray(gt_ego, dtype=np.float64) if gt_ego else np.zeros((0, 7))
                    boxes, scores, elapsed, peak = infer(model, work_bin)
                    keep = scores >= LOWEST_SCORE
                    ious = bev_iou_matrix(boxes[keep], gt_ego_arr)
                    # Rebuild a full-length score vector aligned with the IoU rows.
                    kept_scores = scores[keep]
                    counts = count_matches(ious, kept_scores, len(gt_ego_arr))
                    add_counts(by_vehicle[agent], counts)
                    add_counts(pooled, counts)
                    pred_world = [ego_box_to_world(converter, box, pose) for box in boxes]
                    world_gt.extend([box[:2] for box in gt_world])
                    nn_points.append([box[:2] for box in gt_world])
                    record = {
                        "split": SPLIT,
                        "scenario": item["scenario"],
                        "timestamp": item["timestamp"],
                        "vehicle_id": agent,
                        "run_id": f"bevfusion_single_lidar_validate_vehicle{agent}",
                        "lidar_path": item["pcd"],
                        "ego_pose": pose,
                        "gt_boxes_ego": rows(gt_ego_arr),
                        "gt_boxes_world": gt_world,
                        "pred_boxes_ego": rows(boxes),
                        "pred_boxes_world": pred_world,
                        "scores": [float(v) for v in scores],
                        "inference_seconds": elapsed,
                        "gpu_allocated_peak_bytes": peak,
                        "matches": counts,
                    }
                    handle.write(json.dumps(record) + "\n")
                    handle.flush()
                    times.append(elapsed)
                    peaks.append(peak)
                    max_score = float(scores.max()) if len(scores) else 0.0
                    print(
                        f"VEHICLE {agent} {index}/{len(items)} {item['timestamp']} "
                        f"{elapsed:.3f}s gt {len(gt_ego_arr)} pred {len(scores)} max {max_score:.3f}",
                        flush=True,
                    )
                except Exception as exc:
                    failures.append(f"{agent} {item['timestamp']} {exc}")
                    print(f"FRAME_FAILED {agent} {item['timestamp']} {exc}", flush=True)
        timing[agent] = {
            "frames": len(times),
            "seconds": times,
            "mean_s": float(np.mean(times)) if times else None,
            "median_s": float(np.median(times)) if times else None,
            "min_s": float(np.min(times)) if times else None,
            "max_s": float(np.max(times)) if times else None,
            "mean_excluding_first_s": float(np.mean(times[1:])) if len(times) > 1 else None,
            "total_s": float(np.sum(times)) if times else 0.0,
            "peak_allocated_mib": max(peaks) / 1024**2 if peaks else None,
        }
    if os.path.exists(work_bin):
        os.remove(work_bin)

    import torch

    reserved_peak = int(torch.cuda.max_memory_reserved()) / 1024**2
    recommendation = recommend(pooled, world_gt, nearest_neighbor_distances(nn_points))
    summary = {
        "checkpoint_sha256": digest,
        "weights": weight_report,
        "model_load_peak_allocated_mib": load_peak / 1024**2,
        "inference_peak_reserved_mib": reserved_peak,
        "frame_counts": {agent: len(frames[agent]) for agent in AGENTS},
        "expected_frames_per_vehicle": 30,
        "roundtrip_world_max_m": float(max(roundtrip_errors)) if roundtrip_errors else None,
        "timing": {agent: {k: v for k, v in row.items() if k != "seconds"} for agent, row in timing.items()},
        "timing_seconds": {agent: row["seconds"] for agent, row in timing.items()},
        "failures": failures,
        "recommendation": recommendation,
        "test_split_used": False,
        "agent_0_used": False,
    }
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    write_metrics_csv(os.path.join(OUT, "metrics.csv"), by_vehicle, pooled)
    lines = []
    for agent in AGENTS:
        row = timing[agent]
        lines.append(
            f"TIMING vehicle {agent} n {row['frames']} mean_s {row['mean_s']} "
            f"median_s {row['median_s']} mean_excluding_first_s {row['mean_excluding_first_s']} "
            f"max_s {row['max_s']} peak_allocated_mib {row['peak_allocated_mib']}"
        )
    lines.extend(metric_lines(by_vehicle, pooled))
    lines.append(f"LOAD_PEAK_MIB {load_peak / 1024**2:.2f}")
    lines.append(f"RESERVED_PEAK_MIB {reserved_peak:.2f}")
    lines.append(f"ROUNDTRIP_WORLD_MAX_M {summary['roundtrip_world_max_m']}")
    lines.append(f"RECOMMEND_SCORE {recommendation['score_threshold']}")
    grid = recommendation["grid"]
    lines.append(
        f"RECOMMEND_GRID radius {grid.get('radius_m')} spacing {grid.get('spacing_m')} "
        f"origin {grid.get('origin_xy_m')} n {grid.get('n_circles')} "
        f"multi_vehicle_circles {recommendation['presence_circles_can_contain_multiple_vehicles']}"
    )
    lines.append(f"FAILURES {len(failures)}")
    lines.append("VALIDATION_INFERENCE_DONE")
    text = "\n".join(lines) + "\n"
    with open(os.path.join(OUT, "report.txt"), "w", encoding="utf-8") as handle:
        handle.write(text)
    print(text, flush=True)
    if failures or any(len(frames[agent]) != 30 for agent in AGENTS):
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("VALIDATION_INFERENCE_FAILED")
        sys.exit(1)
