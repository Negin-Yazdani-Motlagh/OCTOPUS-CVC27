"""Sensitivity checks for the CooperScene P2 study.

These checks do not replace the primary 30-frame results. They do not change
the frozen score, radius, or grid, and they do not run the detector.
Octopus-main is imported and not edited.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AUDIT = ROOT / "audit"
sys.path.insert(0, str(AUDIT))

from audit_final import (  # noqa: E402
    AGENTS, BOOTSTRAP_DRAWS, BOOTSTRAP_SEED, METHODS, RADIUS, SPACING,
    audit_files, block_bootstrap, policy_arrays, summarize,
)

FIG = HERE / "figures"
SMOKE_FRAME = "481410"
WINDOW = 72.0
EGO_RADIUS = 3.0
VAL_CANDIDATES = [
    ROOT / "validation_inference",
    Path("/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/validation_inference"),
]


def rotation_matrix(roll: float, yaw: float, pitch: float) -> np.ndarray:
    """Official CooperScene / OpenCOOD x_to_world matrix. Angles are degrees."""
    roll, yaw, pitch = np.radians([roll, yaw, pitch])
    c_y, s_y = np.cos(yaw), np.sin(yaw)
    c_r, s_r = np.cos(roll), np.sin(roll)
    c_p, s_p = np.cos(pitch), np.sin(pitch)
    return np.array([
        [c_p * c_y, c_y * s_p * s_r - s_y * c_r, -c_y * s_p * c_r - s_y * s_r],
        [s_y * c_p, s_y * s_p * s_r + c_y * c_r, -s_y * s_p * c_r + c_y * s_r],
        [s_p, -c_p * s_r, c_p * c_r],
    ])


def in_window(center, pose) -> bool:
    matrix = rotation_matrix(pose[3], pose[4], pose[5])
    delta = np.array([center[0] - pose[0], center[1] - pose[1], 0.0], dtype=np.float64)
    ego = matrix.T @ delta
    return abs(float(ego[0])) <= WINDOW and abs(float(ego[1])) <= WINDOW


def hit(points, circle) -> int:
    limit = RADIUS ** 2
    for point in points:
        if (point[0] - circle[0]) ** 2 + (point[1] - circle[1]) ** 2 <= limit:
            return 1
    return 0


def near_ego(point, pose) -> bool:
    return (point[0] - pose[0]) ** 2 + (point[1] - pose[1]) ** 2 <= EGO_RADIUS ** 2


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def find_validation() -> Path | None:
    for folder in VAL_CANDIDATES:
        needed = [folder / "summary.json"] + [folder / f"vehicle_{agent}.jsonl" for agent in AGENTS]
        if all(path.is_file() for path in needed):
            return folder
    return None


def ego_bound(protocol: dict) -> dict:
    """How many disagreements the ego rule can possibly remove.

    Restoring a dropped box can flip only vehicle 1, and a point on this
    lattice lies in at most two circles. Vehicles 2 and 3 dropped no boxes.
    """
    dropped = {agent: int(protocol["ego_gt"][agent]["removed"]) for agent in AGENTS}
    disagreements = int(protocol["label_disagreements"])
    max_circles_per_box = 2
    max_regions_ego_can_repair = sum(dropped.values()) * max_circles_per_box
    return {
        "status": "bound_from_recorded_ego_drops",
        "disagreements": disagreements,
        "common_regions": int(protocol["common_decisions"]),
        "positive_truth_regions": int(protocol["positive_truth_regions"]),
        "ego_boxes_removed": dropped,
        "max_circles_one_box_can_meet": max_circles_per_box,
        "max_disagreements_ego_rule_can_remove": max_regions_ego_can_repair,
        "disagreements_that_remain_if_every_ego_box_is_restored_at_least": disagreements - max_regions_ego_can_repair,
        "spatial_examples": [],
        "note": (
            "Per-vehicle cause counts and spatial examples need the validation "
            "box files vehicle_1.jsonl, vehicle_2.jsonl, vehicle_3.jsonl, and summary.json. "
            "Those files are not in the local project folder. This bound does not invent them."
        ),
    }


def analyze_ground_truth(folder: Path) -> dict:
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    centers = summary["recommendation"]["grid"]["centers_xy_m"]
    if len(centers) != 144:
        raise SystemExit("SENSITIVITY_GRID_COUNT")
    by_agent = {}
    for agent in AGENTS:
        rows = {}
        for record in load_jsonl(folder / f"vehicle_{agent}.jsonl"):
            if str(record.get("split")) != "validate":
                raise SystemExit("SENSITIVITY_NOT_VALIDATION")
            rows[str(record["timestamp"])] = record
        by_agent[agent] = rows
    timestamps = [set(by_agent[agent]) for agent in AGENTS]
    if not timestamps[0] or timestamps[0] != timestamps[1] or timestamps[1] != timestamps[2]:
        raise SystemExit("SENSITIVITY_TIMESTAMPS")
    roundtrip = []
    cross = []
    vehicle_miss = Counter()
    cause_regions = Counter()
    vehicle_cause = {agent: Counter() for agent in AGENTS}
    missing_pattern = Counter()
    examples = []
    disagreement_points = []
    example_frames = {}
    decisions = 0
    disagreements = 0
    positive = 0
    ego_removed = Counter()
    restored_still = 0
    restored_cleared = 0
    restored_new = 0
    transform_frames = 0
    for token in sorted(timestamps[0], key=int):
        records = {agent: by_agent[agent][token] for agent in AGENTS}
        raw = {}
        kept = {}
        dropped = {}
        poses = {}
        frame_boxes = 0
        for agent, record in records.items():
            pose = [float(v) for v in record["ego_pose"][:6]]
            poses[agent] = pose
            raw_points = []
            kept_points = []
            dropped_points = []
            ego_boxes = record["gt_boxes_ego"]
            world_boxes = record["gt_boxes_world"]
            if len(ego_boxes) != len(world_boxes):
                raise SystemExit("SENSITIVITY_BOX_ALIGNMENT")
            frame_boxes += len(world_boxes)
            for ego_box, world_box in zip(ego_boxes, world_boxes):
                matrix = rotation_matrix(pose[3], pose[4], pose[5])
                back = matrix @ np.asarray(ego_box[:3], dtype=np.float64) + np.asarray(pose[:3], dtype=np.float64)
                roundtrip.append(float(np.max(np.abs(back - np.asarray(world_box[:3], dtype=np.float64)))))
                point = (float(world_box[0]), float(world_box[1]))
                raw_points.append(point)
                if near_ego(point, pose):
                    ego_removed[agent] += 1
                    dropped_points.append(point)
                else:
                    kept_points.append(point)
            raw[agent] = raw_points
            kept[agent] = kept_points
            dropped[agent] = dropped_points
        if frame_boxes:
            transform_frames += 1
        for left, right in (("1", "2"), ("1", "3"), ("2", "3")):
            for point in kept[left]:
                if not kept[right]:
                    continue
                other = np.array(kept[right], dtype=float)
                distance = np.hypot(other[:, 0] - point[0], other[:, 1] - point[1]).min()
                cross.append(float(distance))
        eligible = []
        for index, center in enumerate(centers):
            circle = (float(center[0]), float(center[1]))
            if all(in_window(circle, [float(v) for v in records[agent]["ego_pose"][:6]]) for agent in AGENTS):
                eligible.append((index, circle))
        union = [point for agent in AGENTS for point in kept[agent]]
        raw_union = [point for agent in AGENTS for point in raw[agent]]
        for index, circle in eligible:
            decisions += 1
            truth = hit(union, circle)
            positive += truth
            restored_truth = hit(raw_union, circle)
            restored_hits = [hit(raw[agent], circle) for agent in AGENTS]
            restored_disagree = any(value != restored_truth for value in restored_hits)
            misses = []
            for agent in AGENTS:
                kept_hit = hit(kept[agent], circle)
                if kept_hit == truth:
                    continue
                if truth == 0:
                    raise SystemExit("SENSITIVITY_UNION_BROKEN")
                raw_hit = hit(raw[agent], circle)
                cause = "ego_exclusion" if raw_hit == 1 else "annotation_coverage"
                misses.append((agent, cause))
                vehicle_miss[agent] += 1
                vehicle_cause[agent][cause] += 1
            if misses:
                disagreements += 1
                if restored_disagree:
                    restored_still += 1
                else:
                    restored_cleared += 1
                causes = {cause for _agent, cause in misses}
                if causes == {"ego_exclusion"}:
                    region_cause = "ego_exclusion_only"
                elif causes == {"annotation_coverage"}:
                    region_cause = "annotation_coverage_only"
                else:
                    region_cause = "mixed_ego_and_coverage"
                cause_regions[region_cause] += 1
                missing_pattern["+".join(agent for agent, _cause in misses)] += 1
                disagreement_points.append({
                    "frame_token": token,
                    "x": circle[0],
                    "y": circle[1],
                    "grid_index": index,
                    "region_cause": region_cause,
                })
                if len(examples) < 12:
                    examples.append({
                        "frame_token": token,
                        "center_xy_m": [circle[0], circle[1]],
                        "grid_index": index,
                        "missing": [{"vehicle": agent, "cause": cause} for agent, cause in misses],
                        "region_cause": region_cause,
                    })
                if region_cause not in example_frames:
                    example_frames[region_cause] = {
                        "frame_token": token,
                        "highlight_xy_m": [circle[0], circle[1]],
                        "grid_index": index,
                        "poses_xy_m": {agent: [poses[agent][0], poses[agent][1]] for agent in AGENTS},
                        "kept_xy_m": {agent: [[point[0], point[1]] for point in kept[agent]] for agent in AGENTS},
                        "dropped_xy_m": {agent: [[point[0], point[1]] for point in dropped[agent]] for agent in AGENTS},
                        "circles_xy_m": [[item[1][0], item[1][1]] for item in eligible],
                    }
            elif restored_disagree:
                restored_new += 1
    protocol = json.loads((ROOT / "test_inference" / "protocol_check.json").read_text(encoding="utf-8"))
    if decisions != int(protocol["common_decisions"]) or disagreements != int(protocol["label_disagreements"]):
        raise SystemExit(
            f"SENSITIVITY_REPLAY_MISMATCH decisions {decisions} disagreements {disagreements}"
        )
    cross_arr = np.array(cross) if cross else np.array([np.nan])
    residual = np.asarray(roundtrip, dtype=np.float64)
    if restored_cleared + restored_still != disagreements:
        raise SystemExit("SENSITIVITY_EGO_ACCOUNTING")
    return {
        "status": "replayed_from_validation_boxes",
        "source": str(folder),
        "validation_frames": transform_frames,
        "common_regions": decisions,
        "disagreements": disagreements,
        "positive_truth_regions": positive,
        "agreeing_regions": decisions - disagreements,
        "ego_boxes_removed": {agent: int(ego_removed[agent]) for agent in AGENTS},
        "regions_by_cause": dict(cause_regions),
        "vehicle_misses": {agent: int(vehicle_miss[agent]) for agent in AGENTS},
        "vehicle_cause": {agent: dict(vehicle_cause[agent]) for agent in AGENTS},
        "missing_vehicle_pattern": dict(missing_pattern),
        "ego_restoration": {
            "disagreements_removed": restored_cleared,
            "disagreements_that_remain": restored_still,
            "new_disagreements_if_ego_boxes_are_restored": restored_new,
            "note": (
                "Restoration puts the 3 m ego-dropped boxes back into each vehicle's kept set and into the union. "
                "A removed disagreement is one of the recorded 291 that all three vehicles then hit or all three miss. "
                "A new disagreement is a region that agreed under the frozen rule and would disagree only after that restoration."
            ),
        },
        "coordinate_transform": {
            "boxes": int(residual.size),
            "frames": transform_frames,
            "max_abs_error_m": float(np.max(residual)) if residual.size else None,
            "median_abs_error_m": float(np.median(residual)) if residual.size else None,
            "boxes_above_1e-6_m": int(np.sum(residual > 1e-6)) if residual.size else 0,
            "boxes_above_1e-3_m": int(np.sum(residual > 1e-3)) if residual.size else 0,
            "boxes_above_0.01_m": int(np.sum(residual > 0.01)) if residual.size else 0,
            "method": "Official CooperScene rotation applied to stored gt_boxes_ego, compared with stored gt_boxes_world.",
        },
        "world_from_ego_max_abs_error_m": float(np.max(residual)) if residual.size else None,
        "cross_vehicle_nearest_kept_box_m": {
            "pairs": int(len(cross)),
            "median": float(np.median(cross_arr)),
            "p90": float(np.quantile(cross_arr, 0.90)),
        },
        "spatial_examples": examples,
        "disagreement_points": disagreement_points,
        "example_frames": example_frames,
    }


VEHICLE_COLORS = {"1": "#1f4e79", "2": "#c47b00", "3": "#2f6b4f"}
CAUSE_COLORS = {
    "annotation_coverage_only": "#c47b00",
    "ego_exclusion_only": "#1f4e79",
    "mixed_ego_and_coverage": "#7a1f16",
}


def draw_overview(report: dict, path: Path):
    points = report.get("disagreement_points") or []
    if not points:
        return None
    figure, axis = plt.subplots(figsize=(7.4, 6.2))
    axis.set_aspect("equal")
    for cause, color in CAUSE_COLORS.items():
        chosen = [point for point in points if point["region_cause"] == cause]
        if not chosen:
            continue
        axis.scatter(
            [point["x"] for point in chosen],
            [point["y"] for point in chosen],
            s=18,
            c=color,
            label=f"{cause.replace('_', ' ')} ({len(chosen)})",
            zorder=3,
        )
    axis.set_xlabel("World x (m)")
    axis.set_ylabel("World y (m)")
    axis.set_title("Validation regions whose kept annotations disagree with the union")
    axis.grid(True, linewidth=0.3, alpha=0.4)
    axis.legend(frameon=False, loc="best", fontsize=8)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path.name


def draw_annotation_frame(frame: dict, path: Path, title: str):
    figure, axis = plt.subplots(figsize=(7.6, 6.6))
    axis.set_aspect("equal")
    for center in frame["circles_xy_m"]:
        circle = plt.Circle(center, RADIUS, fill=False, linewidth=0.6, color="#b0b6bd", zorder=1)
        axis.add_patch(circle)
    highlight = frame["highlight_xy_m"]
    axis.add_patch(plt.Circle(highlight, RADIUS, fill=False, linewidth=1.8, color="#7a1f16", zorder=2))
    for agent in AGENTS:
        kept = np.asarray(frame["kept_xy_m"][agent], dtype=float).reshape(-1, 2) if frame["kept_xy_m"][agent] else np.empty((0, 2))
        dropped = np.asarray(frame["dropped_xy_m"][agent], dtype=float).reshape(-1, 2) if frame["dropped_xy_m"][agent] else np.empty((0, 2))
        pose = frame["poses_xy_m"][agent]
        if len(kept):
            axis.scatter(kept[:, 0], kept[:, 1], s=28, c=VEHICLE_COLORS[agent], label=f"vehicle {agent} kept", zorder=4)
        if len(dropped):
            axis.scatter(
                dropped[:, 0], dropped[:, 1], s=46, marker="x", c=VEHICLE_COLORS[agent],
                label=f"vehicle {agent} ego-dropped", zorder=5,
            )
        axis.scatter(pose[0], pose[1], s=70, marker="^", c=VEHICLE_COLORS[agent], edgecolors="black", linewidths=0.4, zorder=6)
    axis.annotate("disagreement", highlight, textcoords="offset points", xytext=(6, 6), fontsize=8, color="#7a1f16")
    axis.set_xlabel("World x (m)")
    axis.set_ylabel("World y (m)")
    axis.set_title(title)
    axis.grid(True, linewidth=0.3, alpha=0.4)
    axis.legend(frameon=False, loc="best", fontsize=7)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path.name


def draw_annotation_plots(report: dict) -> list[str]:
    names = []
    overview = draw_overview(report, FIG / "gt_disagreement_map.png")
    if overview:
        names.append(overview)
    frames = report.get("example_frames") or {}
    coverage = frames.get("annotation_coverage_only")
    if coverage:
        names.append(draw_annotation_frame(
            coverage,
            FIG / "gt_annotation_coverage_example.png",
            f"Coverage disagreement, frame {coverage['frame_token']}, grid_{coverage['grid_index']:03d}",
        ))
    ego_key = "ego_exclusion_only" if "ego_exclusion_only" in frames else "mixed_ego_and_coverage"
    ego_frame = frames.get(ego_key)
    if ego_frame:
        names.append(draw_annotation_frame(
            ego_frame,
            FIG / "gt_ego_exclusion_example.png",
            f"Ego-exclusion disagreement, frame {ego_frame['frame_token']}, grid_{ego_frame['grid_index']:03d}",
        ))
    return names


def unanimous_test_regions(folder: Path, centers, packs, geometry) -> dict:
    """Rescore frozen test labels on regions all three kept annotation sets agree about."""
    by_agent = {}
    for agent in AGENTS:
        path = folder / f"test_boxes_vehicle_{agent}.jsonl"
        if not path.is_file():
            raise SystemExit("SENSITIVITY_TEST_BOXES_MISSING")
        rows = {}
        for record in load_jsonl(path):
            if str(record.get("split")) != "test":
                raise SystemExit("SENSITIVITY_NOT_TEST_BOXES")
            rows[str(record["timestamp"])] = record
        by_agent[agent] = rows
    timestamps = [set(by_agent[agent]) for agent in AGENTS]
    if not timestamps[0] or timestamps[0] != timestamps[1] or timestamps[1] != timestamps[2]:
        raise SystemExit("SENSITIVITY_TEST_TIMESTAMPS")
    unanimous = set()
    common = set()
    positive_unanimous = 0
    positive_common = 0
    for token in sorted(timestamps[0], key=int):
        records = {agent: by_agent[agent][token] for agent in AGENTS}
        kept = {}
        for agent, record in records.items():
            pose = [float(v) for v in record["ego_pose"][:6]]
            points = []
            for box in record["gt_boxes_world"]:
                point = (float(box[0]), float(box[1]))
                if not near_ego(point, pose):
                    points.append(point)
            kept[agent] = points
        union = [point for agent in AGENTS for point in kept[agent]]
        for index, center in enumerate(centers):
            circle = (float(center[0]), float(center[1]))
            if not all(in_window(circle, [float(v) for v in records[agent]["ego_pose"][:6]]) for agent in AGENTS):
                continue
            roi_id = f"grid_{index:03d}"
            common.add((token, roi_id))
            truth = hit(union, circle)
            positive_common += truth
            hits = [hit(kept[agent], circle) for agent in AGENTS]
            if all(value == truth for value in hits):
                unanimous.add((token, roi_id))
                positive_unanimous += truth
    exported = {(row["frame_token"], row["roi_id"]) for frame in geometry for row in frame}
    if common != exported:
        raise SystemExit(
            f"SENSITIVITY_TEST_ROI_MISMATCH common {len(common)} exported {len(exported)} "
            f"only_replay {len(common - exported)} only_export {len(exported - common)}"
        )
    chosen = {method: [] for method in METHODS}
    for frame_index, rows in enumerate(geometry):
        mask = np.array([(row["frame_token"], row["roi_id"]) in unanimous for row in rows])
        if not mask.any():
            continue
        for method in METHODS:
            truth, local, final, accepted = packs[method][frame_index]
            chosen[method].append((truth[mask], local[mask], final[mask], accepted[mask]))
    rows = policy_rows(chosen)
    return {
        "status": "secondary_unanimous_annotation",
        "primary_regions": len(exported),
        "common_regions_replayed": len(common),
        "retained_regions": len(unanimous),
        "retained_labels": len(unanimous) * 3,
        "dropped_regions": len(exported) - len(unanimous),
        "positive_common_regions": positive_common,
        "positive_unanimous_regions": positive_unanimous,
        "policies": rows,
        "note": (
            "Secondary sensitivity only. A region is retained when every vehicle's kept annotations "
            "agree with the union. The primary evaluation remains the union on all exported test regions. "
            "Reliability rates, the score, the radius, and the grid are unchanged."
        ),
    }


def draw_examples(report: dict, path: Path):
    examples = report.get("spatial_examples") or []
    if not examples or report["status"] != "replayed_from_validation_boxes":
        return None
    figure, axis = plt.subplots(figsize=(7.2, 6.0))
    axis.set_aspect("equal")
    colors = {
        "annotation_coverage_only": "#c47b00",
        "ego_exclusion_only": "#1f4e79",
        "mixed_ego_and_coverage": "#7a1f16",
    }
    seen = set()
    for example in examples:
        center = tuple(example["center_xy_m"])
        if center in seen:
            continue
        seen.add(center)
        axis.scatter(center[0], center[1], s=40, c=colors[example["region_cause"]], zorder=3)
        axis.annotate(example["frame_token"][-3:], center, textcoords="offset points", xytext=(4, 4), fontsize=7)
    axis.set_xlabel("World x (m)")
    axis.set_ylabel("World y (m)")
    axis.set_title("Representative validation regions that disagree with the union")
    axis.grid(True, linewidth=0.3, alpha=0.4)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path.name


def write_table(path: Path, rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def policy_rows(packs) -> list[dict]:
    return [summarize(packs[method], method) for method in METHODS]


def subset_packs(packs, tokens, keep: set[str]):
    chosen = [index for index, token in enumerate(tokens) if token in keep]
    return {method: [packs[method][index] for index in chosen] for method in METHODS}, chosen


def draw_r3(blocks: dict, path: Path):
    figure, axis = plt.subplots(figsize=(8.2, 4.8))
    lengths = [1, 2, 5, 10]
    offsets = {1: -0.24, 2: -0.08, 5: 0.08, 10: 0.24}
    colors = {1: "#9aa0a6", 2: "#4c78a8", 5: "#f2a93b", 10: "#e85d4c"}
    labels = [method for method in METHODS if method != "local"]
    for length in lengths:
        for index, method in enumerate(labels):
            low, high = blocks[str(length)][method]["r3"]
            y = index + offsets[length]
            axis.plot([low, high], [y, y], color=colors[length], linewidth=2, solid_capstyle="round")
            axis.plot([(low + high) / 2], [y], marker="o", color=colors[length], markersize=3.5)
    axis.axvline(0, color="#222222", linewidth=0.6)
    axis.set_yticks(range(len(labels)))
    axis.set_yticklabels(labels)
    axis.set_xlabel("R3 minus local, 2.5 to 97.5 percentile")
    axis.set_title("Paired moving-block intervals for the rise in R3")
    handles = [
        plt.Line2D([0], [0], color=colors[length], linewidth=2, label=f"{length} frame" + ("s" if length > 1 else ""))
        for length in lengths
    ]
    axis.legend(handles=handles, frameon=False, loc="lower right")
    axis.grid(True, axis="x", linewidth=0.3, alpha=0.4)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def draw_exclusion(full_rows, held_rows, path: Path):
    figure, axes = plt.subplots(1, 2, figsize=(9.4, 4.2))
    labels = [row["method"] for row in full_rows]
    x = np.arange(len(labels))
    width = 0.36
    for axis, key, title in (
        (axes[0], "mean_error", "Mean error"),
        (axes[1], "r3", "R3"),
    ):
        full = [row[key] for row in full_rows]
        held = [row[key] for row in held_rows]
        axis.bar(x - width / 2, full, width, color="#4c78a8", label="30 frames")
        axis.bar(x + width / 2, held, width, color="#f2a93b", label="29 frames, 481410 held out")
        axis.set_xticks(x)
        axis.set_xticklabels(labels, rotation=30, ha="right")
        axis.set_title(title)
        axis.grid(True, axis="y", linewidth=0.3, alpha=0.4)
    axes[0].legend(frameon=False)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def fmt_interval(pair) -> str:
    return f"[{pair[0]:+.4f}, {pair[1]:+.4f}]"


def findings(gt, r3_rows, exclusion_rows, supported, unanimous) -> str:
    lines = [
        "# Final sensitivity checks",
        "",
        "These three checks are sensitivity analyses. The primary result remains the 30-frame table in `../P2_REPORT.md`. No threshold, radius, or grid value was changed. Detector inference was not rerun. `Octopus-main` was not edited.",
        "",
        "## 1. Ground-truth consistency",
        "",
        "A validation region disagrees when at least one vehicle's own kept annotations miss a circle that the union of the three kept annotation sets hits. The union is the shared truth. A vehicle cannot hit a circle the union misses, because the union contains that vehicle's kept boxes. The recorded count is 291 of 1,047.",
        "",
    ]
    if gt["status"] == "replayed_from_validation_boxes":
        lines.append(f"The validation box files in `{gt['source']}` were replayed with the official rotation, the 3 m ego drop, the ±72 m window, and the 144 stored centers. The replay returned {gt['disagreements']} disagreements on {gt['common_regions']} common regions.")
        lines.append("")
        lines.append("| Vehicle | Misses of a union hit | Ego exclusion | Annotation coverage |")
        lines.append("|---|---:|---:|---:|")
        for agent in AGENTS:
            cause = gt["vehicle_cause"][agent]
            lines.append(
                f"| {agent} | {gt['vehicle_misses'][agent]} | {cause.get('ego_exclusion', 0)} | {cause.get('annotation_coverage', 0)} |"
            )
        lines.append("")
        lines.append("| Region cause | Regions |")
        lines.append("|---|---:|")
        for name, count in sorted(gt["regions_by_cause"].items()):
            lines.append(f"| {name} | {count} |")
        lines.append("")
        transform = gt["coordinate_transform"]
        restore = gt["ego_restoration"]
        lines.append(
            f"The official rotation was applied to every stored ego box on all {transform['frames']} validation frames "
            f"({transform['boxes']} boxes). The largest absolute residual against the stored world box is "
            f"{transform['max_abs_error_m']:.3e} m. "
            f"{transform['boxes_above_1e-6_m']} boxes exceed 1e-6 m, "
            f"{transform['boxes_above_1e-3_m']} exceed 1 mm, and "
            f"{transform['boxes_above_0.01_m']} exceed 1 cm."
        )
        lines.append("")
        lines.append(
            f"Putting the ego-dropped boxes back removes {restore['disagreements_removed']} of the "
            f"{gt['disagreements']} disagreements and leaves {restore['disagreements_that_remain']}. "
            f"That restoration would also create {restore['new_disagreements_if_ego_boxes_are_restored']} disagreements "
            f"on regions that currently agree. Ego exclusion is therefore "
            f"{restore['disagreements_removed']} of the recorded disagreements. "
            f"The other {restore['disagreements_that_remain']} are annotation coverage."
        )
        lines.append("")
        lines.append("| Vehicles missing the union hit | Regions |")
        lines.append("|---|---:|")
        for name, count in sorted(gt["missing_vehicle_pattern"].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"| {name} | {count} |")
        lines.append("")
        lines.append(
            f"The median nearest kept box between two vehicles is {gt['cross_vehicle_nearest_kept_box_m']['median']:.2f} m "
            f"over {gt['cross_vehicle_nearest_kept_box_m']['pairs']} boxes. "
            "The map is `figures/gt_disagreement_map.png`. A coverage example is "
            "`figures/gt_annotation_coverage_example.png` when annotation coverage is present. "
            "An ego-exclusion frame is drawn only when restoring the dropped boxes removes a disagreement."
        )
    else:
        lines.extend([
            "The validation box files are not in the local project folder, so this check does not invent a per-vehicle split or a spatial example. What is recorded, in `protocol_check.json`, is enough for a hard bound.",
            "",
            "Vehicle 1 had 30 annotated boxes removed by the 3 m ego rule. Vehicles 2 and 3 had 0. On the 15 m lattice a point lies in at most two circles of radius 7.5 m, because orthogonal circles only touch at one point and diagonal centers are 21.21 m apart. Restoring every dropped box can therefore change vehicle 1's kept label on at most 60 common regions, and it cannot change vehicle 2 or 3.",
            "",
            f"At most {gt['max_disagreements_ego_rule_can_remove']} of the {gt['disagreements']} disagreements can disappear if the ego rule is undone. At least {gt['disagreements_that_remain_if_every_ego_box_is_restored_at_least']} disagreements remain. Those remaining disagreements are annotation coverage: some vehicle's own boxes, including any box within 3 m of its lidar, do not enter a circle that another vehicle's kept boxes do enter.",
            "",
            "The disagreement counter does not compare coordinate frames. It compares presence in the world-frame circles. The one-frame validation roundtrip, measured when the detector was checked, was 2.13e-14 m. That is not a circle-scale transform error. It is one frame, not a certificate for all 30 validation frames. A transform large enough to create 291 disagreements would have to move boxes across 7.5 m circles. The ego bound shows that the 3 m exclusion cannot do that work.",
            "",
            "No representative map is drawn here. Drawing one from memory would place circles that were not measured.",
        ])
    lines.extend([
        "",
        "This does affect the interpretation of the collective-error results. The shared label is broader than any one vehicle's annotations. A joint miss means all three detectors voted empty on a circle that at least one vehicle's annotators marked. It does not, by itself, mean that all three annotation sets contained that object. The primary scores stay on the union, which is the frozen rule. The 291 disagreements are not detector errors and were not used to choose a threshold.",
        "",
        "## 2. Temporal robustness of R3",
        "",
        "The paired moving-block bootstrap was repeated for the change in R3. Block lengths are 1, 2, 5, and 10 frames. Each length uses 2,000 draws and seed 77232. Blocks do not wrap from frame 481439 back to 481410. The interval is the 2.5 and 97.5 percentiles of policy R3 minus local R3. Length 1 is the published frame bootstrap. Local R3 is 0 on every resample, because no region in the export has all three local labels wrong, so the difference equals the policy's own R3 on each draw.",
        "",
        "| Policy minus local | 1 frame | 2 frames | 5 frames | 10 frames |",
        "|---|---|---|---|---|",
    ])
    for row in r3_rows:
        lines.append(
            f"| {row['method']} | {fmt_interval(row['1'])} | {fmt_interval(row['2'])} | "
            f"{fmt_interval(row['5'])} | {fmt_interval(row['10'])} |"
        )
    lines.extend(["", supported, "",
        "## 3. Smoke-test frame exclusion",
        "",
        "Frame 481410 is the technical smoke-test frame. It is inside the primary 30-frame result. This section holds it out and rescores the same frozen labels. It does not refit the score, the radius, or the grid.",
        "",
        "| Policy | 30-frame mean error | 29-frame mean error | 30-frame R2 | 29-frame R2 | 30-frame R3 | 29-frame R3 | 30-frame joint misses | 29-frame joint misses | 30-frame corrections | 29-frame corrections | 30-frame introduced | 29-frame introduced |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in exclusion_rows:
        lines.append(
            f"| {row['method']} | {row['full_mean_error']:.4f} | {row['held_mean_error']:.4f} | "
            f"{row['full_r2']:.4f} | {row['held_r2']:.4f} | {row['full_r3']:.4f} | {row['held_r3']:.4f} | "
            f"{row['full_joint_false_negatives']} | {row['held_joint_false_negatives']} | "
            f"{row['full_corrections']} | {row['held_corrections']} | "
            f"{row['full_introduced_errors']} | {row['held_introduced_errors']} |"
        )
    lines.extend([
        "",
        "Joint false alarms are in `frame_exclusion.csv`. Holding out 481410 is a sensitivity result. The primary claims stay on all 30 frames.",
        "",
        "## 4. Unanimously annotated test regions",
        "",
        "This is a secondary sensitivity. The primary evaluation remains the union of the three kept annotation sets on every exported test region. A region is retained here only when every vehicle's kept annotations agree with that union. Empty union regions are retained, because a miss by one vehicle would be a disagreement. Reliability rates, the score, the radius, and the grid are the frozen values.",
        "",
    ])
    if unanimous is None:
        lines.append("The per-vehicle test box files were not available, so this rescore was not run.")
    else:
        lines.append(
            f"Replaying the frozen grid on the test box files matched all {unanimous['primary_regions']} exported regions. "
            f"The unanimous subset retains {unanimous['retained_regions']} regions "
            f"({unanimous['retained_labels']} labels) and drops {unanimous['dropped_regions']}. "
            f"{unanimous['positive_unanimous_regions']} of the retained regions are positive, "
            f"out of {unanimous['positive_common_regions']} positive regions in the full union."
        )
        lines.extend([
            "",
            "| Policy | Regions | Mean error | R2 | R3 | Joint false alarms | Joint misses | Corrections | Introduced errors |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for row in unanimous["policies"]:
            lines.append(
                f"| {row['method']} | {row['n_events']} | {row['mean_error']:.4f} | {row['r2']:.4f} | {row['r3']:.4f} | "
                f"{row['joint_false_positives']} | {row['joint_false_negatives']} | "
                f"{row['corrections']} | {row['introduced_errors']} |"
            )
        lines.append("")
        lines.append("These rows do not replace the 1,200-region union table.")
    lines.append("")
    return "\n".join(lines)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    checked = audit_files()
    protocol = json.loads((ROOT / "test_inference" / "protocol_check.json").read_text(encoding="utf-8"))
    folder = find_validation()
    if folder is None:
        gt = ego_bound(protocol)
    else:
        gt = analyze_ground_truth(folder)
        draw_examples(gt, FIG / "gt_disagreement_examples.png")
        draw_annotation_plots(gt)
    stored = {key: value for key, value in gt.items() if key != "example_frames"}
    (HERE / "gt_disagreement.json").write_text(json.dumps(stored, indent=2) + "\n", encoding="utf-8")

    packs, _reasons, _geometry, _expert = policy_arrays(checked)
    tokens = checked["frame_tokens"]
    published = json.loads((AUDIT / "audit_summary.json").read_text(encoding="utf-8"))["block_bootstrap"]
    blocks = {str(length): block_bootstrap(packs, length, BOOTSTRAP_SEED, BOOTSTRAP_DRAWS) for length in (1, 2, 5, 10)}
    for length in ("1", "2", "5", "10"):
        for method in METHODS:
            if method == "local":
                continue
            for key in ("mean_error", "r2", "r3"):
                old = published[length][method][key]
                new = blocks[length][method][key]
                if any(abs(a - b) > 1e-12 for a, b in zip(old, new)):
                    raise SystemExit(f"SENSITIVITY_BOOTSTRAP_DRIFT {length} {method} {key}")
    r3_rows = []
    support_bits = []
    for method in METHODS:
        if method == "local":
            continue
        row = {"method": method}
        above = []
        for length in ("1", "2", "5", "10"):
            pair = blocks[length][method]["r3"]
            row[length] = pair
            above.append(pair[0] > 0)
        r3_rows.append(row)
        support_bits.append((method, all(above), above))
    flat = []
    for row in r3_rows:
        flat.append({
            "method": row["method"],
            "block_1_low": row["1"][0], "block_1_high": row["1"][1],
            "block_2_low": row["2"][0], "block_2_high": row["2"][1],
            "block_5_low": row["5"][0], "block_5_high": row["5"][1],
            "block_10_low": row["10"][0], "block_10_high": row["10"][1],
            "lower_bound_stays_positive": all(row[length][0] > 0 for length in ("1", "2", "5", "10")),
        })
    write_table(HERE / "r3_block_bootstrap.csv", flat)
    draw_r3(blocks, FIG / "r3_block_intervals.png")
    if all(flag for _method, flag, _above in support_bits):
        supported = (
            "The increase in all-agent failures stays supported for every non-local policy at every block length. "
            "Each lower endpoint is above zero. The intervals get somewhat wider as the block grows, and the lower "
            "endpoints move down, so temporal dependence makes the rise less precise. It does not remove it. "
            "This is unfavorable for the policies: accounting for repeated frames still leaves a higher R3 than local."
        )
    else:
        failed = [method for method, flag, _above in support_bits if not flag]
        supported = (
            "The increase in R3 does not stay above zero for every policy and every block length. "
            "Policies whose lower endpoint reaches zero or below: " + ", ".join(failed) + ". "
            "Those rows are unfavorable to a claim that the R3 increase is robust to temporal dependence."
        )

    full = {row["method"]: row for row in policy_rows(packs)}
    keep = {token for token in tokens if token != SMOKE_FRAME}
    if len(keep) != 29 or SMOKE_FRAME not in tokens:
        raise SystemExit("SENSITIVITY_SMOKE_FRAME")
    held_packs, _chosen = subset_packs(packs, tokens, keep)
    held = {row["method"]: row for row in policy_rows(held_packs)}
    exclusion_rows = []
    for method in METHODS:
        left, right = full[method], held[method]
        exclusion_rows.append({
            "method": method,
            "full_regions": left["n_events"],
            "held_regions": right["n_events"],
            "full_mean_error": left["mean_error"],
            "held_mean_error": right["mean_error"],
            "full_r2": left["r2"],
            "held_r2": right["r2"],
            "full_r3": left["r3"],
            "held_r3": right["r3"],
            "full_joint_false_positives": left["joint_false_positives"],
            "held_joint_false_positives": right["joint_false_positives"],
            "full_joint_false_negatives": left["joint_false_negatives"],
            "held_joint_false_negatives": right["joint_false_negatives"],
            "full_corrections": left["corrections"],
            "held_corrections": right["corrections"],
            "full_introduced_errors": left["introduced_errors"],
            "held_introduced_errors": right["introduced_errors"],
        })
    write_table(HERE / "frame_exclusion.csv", exclusion_rows)
    draw_exclusion(
        [full[method] for method in METHODS],
        [held[method] for method in METHODS],
        FIG / "frame_exclusion.png",
    )
    unanimous = None
    if folder is not None and gt["status"] == "replayed_from_validation_boxes":
        summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        centers = summary["recommendation"]["grid"]["centers_xy_m"]
        unanimous = unanimous_test_regions(folder, centers, packs, _geometry)
        write_table(HERE / "unanimous_regions.csv", unanimous["policies"])
    text = findings(gt, r3_rows, exclusion_rows, supported, unanimous)
    (HERE / "FINDINGS.md").write_text(text, encoding="utf-8")
    print(json.dumps({
        "gt_status": gt["status"],
        "disagreements": gt.get("disagreements"),
        "common_regions": gt.get("common_regions"),
        "ego_restoration": gt.get("ego_restoration"),
        "coordinate_transform": gt.get("coordinate_transform"),
        "vehicle_misses": gt.get("vehicle_misses"),
        "vehicle_cause": gt.get("vehicle_cause"),
        "regions_by_cause": gt.get("regions_by_cause"),
        "unanimous_regions": None if unanimous is None else unanimous["retained_regions"],
        "r3_supported": [method for method, flag, _above in support_bits if flag],
        "held_regions": exclusion_rows[0]["held_regions"],
        "figures": sorted(path.name for path in FIG.glob("*.png")),
    }, indent=2))


if __name__ == "__main__":
    main()
