"""One validation frame: official intensity scaling versus the previous raw scaling.

Does not read the test split, does not convert the dataset, and does not
overwrite the smoke-test bin.
"""

import csv
import hashlib
import importlib.util
import json
import os
import sys
import traceback

import numpy as np

DATA_ROOT = "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/data/mini/mini"
REPO = "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/src/CooperScene"
CFG = os.path.join(REPO, "assets/bevfusion/bevfusion_single_lidar.py")
CKPT = os.path.join(REPO, "assets/bevfusion/bevfusion_single_lidar.pth")
CONVERTER = os.path.join(REPO, "tools/dataset_converters/data_converter.py")
OUT = os.environ.get(
    "VALIDATION_OUT",
    "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/detector_validation",
)
EXPECTED_SHA256 = "d71292a772a3f422eb818ab5012a893ee325bffef572524f9c89681eea50f761"
WINDOW = 72.0


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


def find_validation_frame(root):
    split_dir = None
    split_name = None
    for name in ("validate", "val"):
        candidate = os.path.join(root, name)
        if os.path.isdir(candidate):
            split_dir = candidate
            split_name = name
            break
    if split_dir is None:
        raise SystemExit("NO_VALIDATION_SPLIT")

    import yaml

    for agent in ("1", "2", "3"):
        scenarios = sorted(
            d for d in os.listdir(split_dir) if os.path.isdir(os.path.join(split_dir, d))
        )
        for scenario in scenarios:
            agent_dir = os.path.join(split_dir, scenario, agent)
            if not os.path.isdir(agent_dir):
                continue
            names = sorted(
                name
                for name in os.listdir(agent_dir)
                if name.endswith(".yaml")
                and not name.startswith("data_protocol")
                and not name.endswith("_additional.yaml")
            )
            for name in names:
                yaml_path = os.path.join(agent_dir, name)
                pcd_path = os.path.join(agent_dir, name.replace(".yaml", ".pcd"))
                if not os.path.isfile(pcd_path):
                    continue
                with open(yaml_path, "r", encoding="utf-8") as handle:
                    meta = yaml.unsafe_load(handle)
                vehicles = meta.get("vehicles") or {}
                pose = meta.get("lidar_pose", meta.get("true_ego_pos"))
                if isinstance(vehicles, dict) and vehicles and pose is not None:
                    return {
                        "split": split_name,
                        "scenario": scenario,
                        "agent": agent,
                        "yaml": yaml_path,
                        "pcd": pcd_path,
                        "meta": meta,
                    }
    raise SystemExit("NO_VALIDATION_FRAME_WITH_VEHICLES")


def write_raw_bin(pcd_path, bin_path):
    import open3d as o3d

    cloud = o3d.t.io.read_point_cloud(pcd_path)
    xyz = cloud.point["positions"].numpy().astype(np.float32)
    intensity = cloud.point["intensity"].numpy().astype(np.float32).reshape(-1, 1)
    points = np.hstack([xyz, intensity]).astype(np.float32)
    points.tofile(bin_path)
    return points.shape[0]


def intensity_stats(bin_path):
    points = np.fromfile(bin_path, dtype=np.float32).reshape(-1, 4)
    column = points[:, 3]
    return {
        "points": int(points.shape[0]),
        "min": float(column.min()),
        "max": float(column.max()),
        "mean": float(column.mean()),
        "p50": float(np.percentile(column, 50)),
        "p99": float(np.percentile(column, 99)),
    }


def ground_truth_boxes(converter, meta):
    pose = meta.get("lidar_pose", meta.get("true_ego_pos"))
    boxes = []
    for _veh_id, veh in meta["vehicles"].items():
        box = converter.parse_cooperscene_vehicle(veh, pose)
        if box is not None:
            boxes.append(box)
    if not boxes:
        return np.zeros((0, 7), dtype=np.float64)
    return np.asarray(boxes, dtype=np.float64)


def in_window(boxes):
    if len(boxes) == 0:
        return np.zeros((0,), dtype=bool)
    return (np.abs(boxes[:, 0]) <= WINDOW) & (np.abs(boxes[:, 1]) <= WINDOW)


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
            ious[i, j] = pred.intersection(gt).area / union
    return ious


def match_report(scores, ious, gt_in):
    n_in = int(gt_in.sum()) if getattr(gt_in, "size", 0) else 0
    usable = ious[:, gt_in] if ious.size else np.zeros((len(scores), n_in), dtype=np.float64)
    per_gt = []
    if usable.shape[1]:
        for j in range(usable.shape[1]):
            best = int(np.argmax(usable[:, j])) if len(scores) else -1
            per_gt.append(
                {
                    "gt_index": int(np.flatnonzero(gt_in)[j]),
                    "best_iou": float(usable[best, j]) if best >= 0 else 0.0,
                    "pred_index": best,
                    "pred_score": float(scores[best]) if best >= 0 else None,
                }
            )
    best_any = float(usable.max()) if usable.size else 0.0
    summary = {"best_bev_iou_in_window": best_any, "per_gt_in_window": per_gt}
    for thr in (0.05, 0.1, 0.3, 0.5):
        keep = scores >= thr
        kept = int(keep.sum())
        if kept and usable.shape[1]:
            best_per_pred = usable[keep].max(axis=1)
            matched = int((best_per_pred >= 0.5).sum())
            best = float(best_per_pred.max())
        else:
            matched = 0
            best = 0.0
        summary[f"score_ge_{thr}"] = {
            "predictions": kept,
            "predictions_with_bev_iou_ge_0.5": matched,
            "best_bev_iou": best,
        }
    if per_gt:
        summary["gt_with_bev_iou_ge_0.5"] = int(sum(row["best_iou"] >= 0.5 for row in per_gt))
        summary["gt_with_bev_iou_ge_0.1"] = int(sum(row["best_iou"] >= 0.1 for row in per_gt))
        summary["gt_in_window"] = len(per_gt)
    else:
        summary["gt_with_bev_iou_ge_0.5"] = 0
        summary["gt_with_bev_iou_ge_0.1"] = 0
        summary["gt_in_window"] = 0
    return summary


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
    boxes = instances.bboxes_3d
    tensor = boxes.tensor if hasattr(boxes, "tensor") else boxes
    array = tensor.detach().cpu().numpy().astype(np.float64)
    return array[:, :7], scores


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
    permuted = []
    mismatched = []
    absent = []
    for key, value in state.items():
        target = key[7:] if key.startswith("module.") else key
        if target not in own:
            absent.append(target)
            continue
        have = tuple(value.shape)
        want = tuple(own[target].shape)
        if have == want:
            fixed[target] = value
        elif value.ndim == 5 and tuple(value.permute(1, 2, 3, 4, 0).shape) == want:
            fixed[target] = value.permute(1, 2, 3, 4, 0).contiguous()
            permuted.append({"key": target, "checkpoint": list(have), "model": list(want)})
        else:
            mismatched.append({"key": target, "checkpoint": list(have), "model": list(want)})
    missing, unexpected = model.load_state_dict(fixed, strict=False)
    model.eval()
    report = {
        "checkpoint_top_level_keys": [str(k) for k in blob.keys()] if hasattr(blob, "keys") else [],
        "checkpoint_tensors": len(state),
        "copied_same_shape": len(fixed) - len(permuted),
        "permuted": len(permuted),
        "permuted_examples": permuted[:8],
        "still_mismatched": mismatched,
        "checkpoint_keys_absent_from_model": absent,
        "missing_keys": list(missing),
        "unexpected_keys": list(unexpected),
        "model_class": type(model).__name__,
        "device": str(next(model.parameters()).device),
    }
    return model, report


def run_inference(model, bin_path):
    import torch
    from mmdet3d.apis import inference_detector

    with torch.no_grad():
        result = inference_detector(model, bin_path)
    instances = find_instances(result)
    if instances is None:
        raise RuntimeError(f"NO_PRED_INSTANCES type={type(result).__name__}")
    boxes, scores = boxes_and_scores(instances)
    return {
        "result_type": type(result).__name__,
        "result_len": len(result) if isinstance(result, (list, tuple)) else None,
        "boxes": boxes,
        "scores": scores,
    }


def score_summary(scores):
    if len(scores) == 0:
        return {"count": 0, "max": None, "mean_top10": None}
    order = np.sort(scores)[::-1]
    top = order[:10]
    return {
        "count": int(len(scores)),
        "max": float(order[0]),
        "mean_top10": float(top.mean()),
        "ge_0.05": int((scores >= 0.05).sum()),
        "ge_0.1": int((scores >= 0.1).sum()),
        "ge_0.3": int((scores >= 0.3).sum()),
        "ge_0.5": int((scores >= 0.5).sum()),
        "finite": bool(np.isfinite(scores).all()),
    }


def draw_boxes(ax, boxes, color, scores=None):
    for index, box in enumerate(boxes):
        corners = bev_corners(box)
        closed = np.vstack([corners, corners[:1]])
        alpha = 0.9
        if scores is not None:
            alpha = float(np.clip(scores[index] / max(float(scores.max()), 1e-6), 0.25, 0.95))
        ax.plot(closed[:, 0], closed[:, 1], color=color, linewidth=1.2, alpha=alpha)


def save_plots(out_dir, gt, gt_in, raw, official):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def panel(ax, pred, title):
        ax.set_title(title, fontsize=9)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(-80, 80)
        ax.set_ylim(-80, 80)
        ax.axhline(0, color="0.85", linewidth=0.4)
        ax.axvline(0, color="0.85", linewidth=0.4)
        ax.add_patch(plt.Rectangle((-72, -72), 144, 144, fill=False, linestyle="--", linewidth=0.6, color="0.5"))
        if len(gt):
            outside = ~gt_in
            if outside.any():
                draw_boxes(ax, gt[outside], "0.75")
            if gt_in.any():
                draw_boxes(ax, gt[gt_in], "green")
        scores = pred["scores"]
        boxes = pred["boxes"]
        if len(scores) == 0:
            ax.text(0, 0, "no boxes", ha="center")
            return
        if scores.max() >= 0.05:
            keep = np.flatnonzero(scores >= 0.05)
            if len(keep) > 80:
                keep = np.argsort(-scores)[:80]
            caption = "predictions with score >= 0.05"
        else:
            keep = np.argsort(-scores)[:20]
            caption = "top 20 scores (all below 0.05)"
        draw_boxes(ax, boxes[keep], "crimson", scores[keep])
        ax.set_xlabel(caption, fontsize=8)

    figure, axes = plt.subplots(1, 2, figsize=(11, 5.5))
    def headline(pred, label):
        score = pred["score_summary"]["max"]
        score_text = "none" if score is None else f"{score:.4f}"
        iou = pred["match"]["best_bev_iou_in_window"]
        return f"{label}\nmax score {score_text}  best BEV IoU {iou:.3f}"

    panel(axes[0], raw, headline(raw, "Previous raw intensity"))
    panel(axes[1], official, headline(official, "Official intensity / 65535"))
    figure.suptitle(
        "Validation frame. Green: ground truth inside 72 m. Gray: ground truth outside that window.",
        fontsize=10,
    )
    figure.tight_layout()
    figure.savefig(os.path.join(out_dir, "bev_side_by_side.png"), dpi=140)
    plt.close(figure)

    for name, pred in (("bev_previous.png", raw), ("bev_official.png", official)):
        figure, ax = plt.subplots(figsize=(6, 6))
        panel(ax, pred, name)
        figure.tight_layout()
        figure.savefig(os.path.join(out_dir, name), dpi=140)
        plt.close(figure)


def write_match_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["gt_index", "best_iou", "pred_index", "pred_score"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    os.makedirs(OUT, exist_ok=True)
    converter = load_converter()
    frame = find_validation_frame(DATA_ROOT)
    official_bin = os.path.join(OUT, "official_intensity.bin")
    raw_bin = os.path.join(OUT, "previous_raw_intensity.bin")
    if not converter.convert_pcd_to_bin(frame["pcd"], official_bin):
        raise SystemExit("OFFICIAL_CONVERT_FAILED")
    raw_points = write_raw_bin(frame["pcd"], raw_bin)
    official_stats = intensity_stats(official_bin)
    raw_stats = intensity_stats(raw_bin)
    gt = ground_truth_boxes(converter, frame["meta"])
    gt_mask = in_window(gt)
    np.save(os.path.join(OUT, "gt_boxes_ego.npy"), gt)

    digest = sha256_file(CKPT)
    model, weight_report = load_model()
    import torch

    raw_pred = run_inference(model, raw_bin)
    torch.cuda.empty_cache()
    official_pred = run_inference(model, official_bin)

    def pack(pred, gt_boxes, mask):
        ious = bev_iou_matrix(pred["boxes"], gt_boxes)
        match = match_report(pred["scores"], ious, mask)
        return {
            "boxes": pred["boxes"],
            "scores": pred["scores"],
            "score_summary": score_summary(pred["scores"]),
            "match": match,
            "result_type": pred["result_type"],
            "result_len": pred["result_len"],
        }

    raw = pack(raw_pred, gt, gt_mask)
    official = pack(official_pred, gt, gt_mask)
    np.save(os.path.join(OUT, "boxes_previous.npy"), raw["boxes"])
    np.save(os.path.join(OUT, "scores_previous.npy"), raw["scores"])
    np.save(os.path.join(OUT, "boxes_official.npy"), official["boxes"])
    np.save(os.path.join(OUT, "scores_official.npy"), official["scores"])
    write_match_csv(os.path.join(OUT, "matches_previous.csv"), raw["match"]["per_gt_in_window"])
    write_match_csv(os.path.join(OUT, "matches_official.csv"), official["match"]["per_gt_in_window"])
    save_plots(OUT, gt, gt_mask, raw, official)

    summary = {
        "frame": {k: frame[k] for k in ("split", "scenario", "agent", "yaml", "pcd")},
        "official_converter": CONVERTER,
        "official_intensity_divisor": 65535.0,
        "previous_script_divides_intensity": False,
        "raw_points_written": raw_points,
        "intensity_previous": raw_stats,
        "intensity_official": official_stats,
        "intensity_max_ratio_previous_over_official": (
            raw_stats["max"] / official_stats["max"] if official_stats["max"] else None
        ),
        "checkpoint_sha256": digest,
        "checkpoint_sha256_matches_published": digest == EXPECTED_SHA256,
        "weights": weight_report,
        "ground_truth_boxes": int(len(gt)),
        "ground_truth_in_window": int(gt_mask.sum()),
        "previous_raw": {
            "result_type": raw["result_type"],
            "result_len": raw["result_len"],
            "scores": raw["score_summary"],
            "bev_iou": {k: v for k, v in raw["match"].items() if k != "per_gt_in_window"},
        },
        "official_normalized": {
            "result_type": official["result_type"],
            "result_len": official["result_len"],
            "scores": official["score_summary"],
            "bev_iou": {k: v for k, v in official["match"].items() if k != "per_gt_in_window"},
        },
        "diagnostic_thresholds_are_not_a_frozen_cutoff": True,
        "test_split_used": False,
    }
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    lines = [
        f"FRAME {frame['split']}/{frame['scenario']}/{frame['agent']} {os.path.basename(frame['pcd'])}",
        f"INTENSITY_PREVIOUS min {raw_stats['min']:.6g} max {raw_stats['max']:.6g}",
        f"INTENSITY_OFFICIAL min {official_stats['min']:.6g} max {official_stats['max']:.6g}",
        f"SHA256_MATCH {digest == EXPECTED_SHA256}",
        f"PERMUTED {weight_report['permuted']}",
        f"STILL_MISMATCHED {len(weight_report['still_mismatched'])}",
        f"MISSING_KEYS {len(weight_report['missing_keys'])}",
        f"UNEXPECTED_KEYS {len(weight_report['unexpected_keys'])}",
        f"CHECKPOINT_KEYS_ABSENT {len(weight_report['checkpoint_keys_absent_from_model'])}",
        f"GT_BOXES {len(gt)} IN_WINDOW {int(gt_mask.sum())}",
        f"PREVIOUS_MAX_SCORE {raw['score_summary']['max']}",
        f"OFFICIAL_MAX_SCORE {official['score_summary']['max']}",
        f"PREVIOUS_BEST_BEV_IOU {raw['match']['best_bev_iou_in_window']}",
        f"OFFICIAL_BEST_BEV_IOU {official['match']['best_bev_iou_in_window']}",
        f"OFFICIAL_GT_IOU_GE_0.5 {official['match']['gt_with_bev_iou_ge_0.5']}",
        f"PREVIOUS_GT_IOU_GE_0.5 {raw['match']['gt_with_bev_iou_ge_0.5']}",
        "VALIDATION_DONE",
    ]
    report_path = os.path.join(OUT, "report.txt")
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("VALIDATION_FAILED")
        sys.exit(1)
