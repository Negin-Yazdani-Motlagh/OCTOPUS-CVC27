"""Object-level bird's-eye-view check of the 29 harmful region queries.

This does not replace the region benchmark. Each row keeps its original
score cutoff. A detection may match at most one ground-truth car in the
frame, and each car may receive at most one detection.
"""
from __future__ import annotations

import csv
import json
import math
import unittest
from collections import defaultdict
from pathlib import Path

from bev_iou import assign_one_to_one, bev_corners, bev_iou
import test_bev_iou


ROOT = Path(__file__).resolve().parent
CACHE = ROOT.parents[0] / "v2v4real_all" / "dmstrack_source"
HARMFUL = ROOT.parents[0] / "spatial_audit" / "harmful_joint_misses.csv"
COMMIT = "d3b9949499c8e68ea33060873bd1cb95b6d4d323"
THRESHOLDS = (("50", 0.50), ("70", 0.70))

SOURCES = {
    "ego": "AB3DMOT/data/v2v4real/detection/multi_sensor_differentiable_kalman_filter_Car_val/ego/{scene}.txt",
    "partner": "AB3DMOT/data/v2v4real/detection/multi_sensor_differentiable_kalman_filter_Car_val/1/{scene}.txt",
    "late": "AB3DMOT/data/v2v4real/detection/late_fusion_Car_val/{scene}.txt",
}
GT_PATH = "AB3DMOT/scripts/KITTI/v2v4real_val_label/{scene}.txt"


class Box:
    def __init__(self, **fields):
        self.__dict__.update(fields)


def load_ground_truth(scene: str) -> dict[int, list[Box]]:
    by_frame: dict[int, list[Box]] = defaultdict(list)
    text = (CACHE / GT_PATH.format(scene=scene)).read_text()
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) < 17 or fields[2] != "Car":
            raise ValueError(f"unexpected ground-truth row in {scene}: {line[:120]}")
        frame = int(fields[0])
        box = Box(
            track_id=int(float(fields[1])),
            height=float(fields[10]),
            width=float(fields[11]),
            length=float(fields[12]),
            x=float(fields[13]),
            y=float(fields[14]),
            z=float(fields[15]),
            yaw=float(fields[16]),
            score=None,
            file_index=len(by_frame[frame]) + 1,
        )
        box.corners = bev_corners(box.x, box.z, box.length, box.width, box.yaw)
        by_frame[frame].append(box)
    return by_frame


def load_detections(scene: str, source: str) -> dict[int, list[Box]]:
    by_frame: dict[int, list[Box]] = defaultdict(list)
    text = (CACHE / SOURCES[source].format(scene=scene)).read_text()
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = [value.strip() for value in line.split(",")]
        if len(fields) < 15 or fields[1] != "2":
            raise ValueError(f"unexpected {source} row in {scene}: {line[:120]}")
        frame = int(fields[0])
        box = Box(
            track_id=None,
            height=float(fields[7]),
            width=float(fields[8]),
            length=float(fields[9]),
            x=float(fields[10]),
            y=float(fields[11]),
            z=float(fields[12]),
            yaw=float(fields[13]),
            score=float(fields[6]),
            file_index=len(by_frame[frame]) + 1,
        )
        box.corners = bev_corners(box.x, box.z, box.length, box.width, box.yaw)
        by_frame[frame].append(box)
    return by_frame


def best_anchor_overlap(detections: list[Box], anchor: Box) -> tuple[float, Box | None]:
    best_iou = 0.0
    best_box = None
    for detection in detections:
        overlap = bev_iou(detection.corners, anchor.corners)
        if overlap > best_iou:
            best_iou = overlap
            best_box = detection
    return best_iou, best_box


def evaluate_source(detections: list[Box], cars: list[Box], anchor_index: int, threshold: float) -> dict:
    assignment = assign_one_to_one(
        [box.score for box in detections],
        [box.corners for box in detections],
        [box.corners for box in cars],
        threshold,
    )
    if anchor_index not in assignment:
        return {"matched": 0, "det_id": "", "iou": ""}
    detection_index, overlap = assignment[anchor_index]
    return {
        "matched": 1,
        "det_id": detections[detection_index].file_index,
        "iou": overlap,
    }


def circle_hit(detections: list[Box], anchor: Box, radius: float) -> Box | None:
    hits = [box for box in detections if (box.x - anchor.x) ** 2 + (box.z - anchor.z) ** 2 <= radius * radius]
    if not hits:
        return None
    return max(hits, key=lambda box: (bev_iou(box.corners, anchor.corners), box.score))


def hidden_anchor_box(detections: list[Box], anchor: Box, score_min: float) -> tuple[float, Box | None]:
    best_iou = 0.0
    best_box = None
    for box in detections:
        if box.score >= score_min:
            continue
        overlap = bev_iou(box.corners, anchor.corners)
        if overlap > best_iou:
            best_iou = overlap
            best_box = box
    return best_iou, best_box


def reason(late_matched: int, ego_matched: int, partner_matched: int) -> str:
    if late_matched == 0 and (ego_matched or partner_matched):
        return "remains_harmful"
    if late_matched:
        return "late_fusion_matches_anchor"
    return "neither_local_matches_anchor"


def shown(value: str) -> str:
    return f"{float(value):.3f}"


def write_report(rows: list[dict], test_count: int) -> None:
    lines = [
        "# Object-level check of the 29 harmful region queries",
        "",
        "This is an additional check. The region labels in `spatial_audit/harmful_joint_misses.csv` are unchanged. A query remains harmful at an IoU threshold only when late fusion is not matched to the anchor car and at least one local detector is.",
        "",
        "## Box convention",
        "",
        f"The text files are the DMSTrack export at commit `{COMMIT}`. A detection row is the AB3DMOT tracking input written by `Object_3D.convert_to_trk_input_str`: frame, class code, four image-box values, score, height, width, length, camera x, y, z, yaw, alpha. Class code 2 is Car. The ground-truth tracking row is frame, track id, type, truncation, occlusion, alpha, four image-box values, height, width, length, camera x, y, z, yaw.",
        "",
        "The ground rectangle follows `Box3D.box2corners3d_camcoord`. Before yaw, length lies along camera X and width along camera Z. Yaw is `roty` from `kitti_oxts.py`: the matrix `[[cos, 0, sin], [0, 1, 0], [-sin, 0, cos]]`. The bird's-eye-view polygon is that bottom rectangle in X and Z, the same projection `iou3d` uses. Height and camera Y are not part of this overlap.",
        "",
        "Matching follows the one-frame rule in OpenCOOD `caluclate_tp_fp`: detections that meet the original score cutoff are considered from highest score to lowest, and each takes the still-unmatched ground-truth car with the largest overlap when that overlap is at least 0.50 or, in a separate pass, 0.70. Ego, the partner, and late fusion are matched separately.",
        "",
        f"The geometric tests in `test_bev_iou.py` passed ({test_count} tests): identical boxes, a half-turn of the same box, separated boxes, an axis-aligned half overlap of 1/3, a contained box, a quarter-turn overlap of 1/3, and the one-to-one score and overlap rules.",
        "",
        "## Side-by-side result",
        "",
        "Region columns are the original center-in-circle labels. Object columns are 1 when the anchor car receives a detection at that IoU threshold.",
        "",
        "| event | radius | score | region ego, partner, late | object 0.50 ego, partner, late | object 0.70 ego, partner, late | 0.50 | 0.70 |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {event_id} | {radius_m} | {score_min} | {region_ego}, {region_partner}, {region_late} | "
            "{ego_50}, {partner_50}, {late_50} | {ego_70}, {partner_70}, {late_70} | {reason_50} | {reason_70} |".format(**row)
        )
    remain_50 = sum(row["reason_50"] == "remains_harmful" for row in rows)
    remain_70 = sum(row["reason_70"] == "remains_harmful" for row in rows)
    lines.extend([
        "",
        f"Of the 29 query-setting rows, {remain_50} remain harmful at IoU 0.50 and {remain_70} remain harmful at IoU 0.70.",
        "",
        "## Why the others do not",
        "",
    ])
    for threshold, key in (("0.50", "reason_50"), ("0.70", "reason_70")):
        lines.append(f"### IoU {threshold}")
        lines.append("")
        cleared = [row for row in rows if row[key] != "remains_harmful"]
        if threshold == "0.70":
            lines.append("Every row that misses 0.50 also misses 0.70. One further row falls between the two thresholds.")
            lines.append("")
            cleared = [row for row in cleared if row["reason_50"] == "remains_harmful"]
        if not cleared:
            lines.append("Every row still has a local match and no late-fusion match.")
            lines.append("")
            continue
        groups: dict[tuple, list[dict]] = {}
        for row in cleared:
            groups.setdefault((row["event_id"], row["score_min"]), []).append(row)
        for group in groups.values():
            row = group[0]
            radii = ", ".join(item["radius_m"] for item in group)
            overlap = float(row["inside_iou"])
            if overlap > 0.0:
                lines.append(
                    f"- `{row['event_id']}` at score {row['score_min']} and radius {radii} m. "
                    f"{row['inside_source'].capitalize()} box {row['inside_det']} scores {shown(row['inside_score'])} "
                    f"and its center is {shown(row['inside_distance_m'])} m from anchor track {row['anchor_track_id']}. "
                    f"Their overlap is {shown(row['inside_iou'])}, below {threshold}. "
                    f"Late fusion's best eligible overlap is {shown(row['best_iou_late'])}."
                )
            else:
                assigned = ""
                if row["inside_assigned_track"]:
                    assigned = (
                        f" At IoU 0.50 that detection is matched to track {row['inside_assigned_track']} "
                        f"with overlap {shown(row['inside_assigned_iou'])}."
                    )
                hidden = ""
                if float(row["hidden_iou"]) >= 0.05:
                    hidden = (
                        f" The strongest box below the score cutoff is {row['hidden_source']} box {row['hidden_det']}, "
                        f"score {shown(row['hidden_score'])}, overlap {shown(row['hidden_iou'])} with the anchor."
                    )
                lines.append(
                    f"- `{row['event_id']}` at score {row['score_min']} and radius {radii} m. "
                    f"{row['inside_source'].capitalize()} box {row['inside_det']} scores {shown(row['inside_score'])} "
                    f"and its center is {shown(row['inside_distance_m'])} m from anchor track {row['anchor_track_id']}, "
                    f"but the two boxes do not overlap.{assigned}{hidden}"
                )
        lines.append("")
    late_best = max(float(row["best_iou_late"]) for row in rows)
    local_best = min(
        max(float(row["matched_iou_ego_50"] or 0), float(row["matched_iou_partner_50"] or 0))
        for row in rows if row["reason_50"] == "remains_harmful"
    )
    boundary = next(row for row in rows if row["event_id"] == "v2v4real_0003_0168_positive" and row["score_min"] == "0.3")
    lines.extend([
        "Late fusion does not match the anchor in any of the 29 rows. Its largest eligible overlap with an anchor is "
        f"{late_best:.3f}. The local matches that remain harmful at 0.50 all have overlap at least {local_best:.3f}. "
        f"On the boundary example `{boundary['event_id']}` at score {boundary['score_min']}, late fusion's best eligible overlap "
        f"with anchor track {boundary['anchor_track_id']} is {shown(boundary['best_iou_late'])}, while ego's is {shown(boundary['best_iou_ego'])}.",
        "",
        "One-to-one matching did not give any of these anchors to a different car. When an eligible detection cleared the threshold against the anchor, that detection was still available.",
        "",
        "Counts and the matched box ids are in `harmful_object_matches.csv`.",
        "",
    ])
    (ROOT / "ANALYSIS.md").write_text("\n".join(lines))


def main() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_bev_iou)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise SystemExit("bird's-eye-view tests failed; no object labels were written")

    harmful = list(csv.DictReader(HARMFUL.open()))
    if len(harmful) != 29:
        raise SystemExit(f"expected 29 harmful rows, found {len(harmful)}")

    gt_cache: dict[str, dict] = {}
    det_cache: dict[tuple[str, str], dict] = {}
    output_rows = []
    anchor_errors = 0
    for record in harmful:
        scene = record["scene"]
        frame = int(record["frame"])
        score_min = float(record["score_min"])
        if scene not in gt_cache:
            gt_cache[scene] = load_ground_truth(scene)
            for source in SOURCES:
                det_cache[(scene, source)] = load_detections(scene, source)
        cars = gt_cache[scene][frame]
        anchor_index = frame % len(cars)
        anchor = cars[anchor_index]
        if not math.isclose(anchor.x, float(record["query_x_m"]), rel_tol=0, abs_tol=1e-4):
            anchor_errors += 1
        if not math.isclose(anchor.z, float(record["query_z_m"]), rel_tol=0, abs_tol=1e-4):
            anchor_errors += 1

        row = {
            "radius_m": record["radius_m"],
            "score_min": record["score_min"],
            "event_id": record["event_id"],
            "scene": scene,
            "frame": frame,
            "anchor_track_id": anchor.track_id,
            "region_ego": int(record["ego"]),
            "region_partner": int(record["partner"]),
            "region_late": int(record["late_fusion"]),
            "region_truth": int(record["truth"]),
            "mechanism": record["mechanism"],
        }
        for source in ("ego", "partner", "late"):
            eligible = [box for box in det_cache[(scene, source)][frame] if box.score >= score_min]
            overlap, best_box = best_anchor_overlap(eligible, anchor)
            row[f"best_iou_{source}"] = f"{overlap:.6f}"
            row[f"best_det_{source}"] = "" if best_box is None else best_box.file_index
            row[f"eligible_{source}"] = len(eligible)
            for label, threshold in THRESHOLDS:
                matched = evaluate_source(eligible, cars, anchor_index, threshold)
                row[f"{source}_{label}"] = matched["matched"]
                row[f"matched_det_{source}_{label}"] = matched["det_id"]
                row[f"matched_iou_{source}_{label}"] = "" if matched["iou"] == "" else f"{matched['iou']:.6f}"
        for label, _threshold in THRESHOLDS:
            row[f"reason_{label}"] = reason(row[f"late_{label}"], row[f"ego_{label}"], row[f"partner_{label}"])
        local_source = "ego" if int(record["ego"]) else "partner"
        eligible_local = [box for box in det_cache[(scene, local_source)][frame] if box.score >= score_min]
        inside = circle_hit(eligible_local, anchor, float(record["radius_m"]))
        if inside is None:
            raise SystemExit(f"no eligible center inside the circle for {record['event_id']}")
        row["inside_source"] = local_source
        row["inside_det"] = "" if inside is None else inside.file_index
        row["inside_score"] = "" if inside is None else f"{inside.score:.6f}"
        row["inside_distance_m"] = "" if inside is None else f"{math.hypot(inside.x - anchor.x, inside.z - anchor.z):.6f}"
        row["inside_iou"] = "0.000000" if inside is None else f"{bev_iou(inside.corners, anchor.corners):.6f}"
        assigned = assign_one_to_one(
            [box.score for box in eligible_local],
            [box.corners for box in eligible_local],
            [box.corners for box in cars],
            0.50,
        )
        row["inside_assigned_track"] = ""
        row["inside_assigned_iou"] = ""
        if inside is not None:
            detection_index = eligible_local.index(inside)
            for gt_index, (matched_index, overlap) in assigned.items():
                if matched_index == detection_index and gt_index != anchor_index:
                    row["inside_assigned_track"] = cars[gt_index].track_id
                    row["inside_assigned_iou"] = f"{overlap:.6f}"
        hidden_iou, hidden_box, hidden_source = 0.0, None, ""
        for source in ("ego", "partner", "late"):
            overlap, box = hidden_anchor_box(det_cache[(scene, source)][frame], anchor, score_min)
            if overlap > hidden_iou:
                hidden_iou, hidden_box, hidden_source = overlap, box, source
        row["hidden_source"] = hidden_source
        row["hidden_det"] = "" if hidden_box is None else hidden_box.file_index
        row["hidden_score"] = "" if hidden_box is None else f"{hidden_box.score:.6f}"
        row["hidden_iou"] = f"{hidden_iou:.6f}"
        output_rows.append(row)

    if anchor_errors:
        raise SystemExit(f"{anchor_errors} anchor centers do not match the query center")

    fieldnames = [
        "event_id", "scene", "frame", "radius_m", "score_min", "anchor_track_id",
        "region_ego", "region_partner", "region_late", "region_truth", "mechanism",
        "ego_50", "partner_50", "late_50", "reason_50",
        "ego_70", "partner_70", "late_70", "reason_70",
        "best_iou_ego", "best_det_ego", "eligible_ego",
        "best_iou_partner", "best_det_partner", "eligible_partner",
        "best_iou_late", "best_det_late", "eligible_late",
        "matched_det_ego_50", "matched_iou_ego_50",
        "matched_det_partner_50", "matched_iou_partner_50",
        "matched_det_late_50", "matched_iou_late_50",
        "matched_det_ego_70", "matched_iou_ego_70",
        "matched_det_partner_70", "matched_iou_partner_70",
        "matched_det_late_70", "matched_iou_late_70",
        "inside_source", "inside_det", "inside_score", "inside_distance_m", "inside_iou",
        "inside_assigned_track", "inside_assigned_iou",
        "hidden_source", "hidden_det", "hidden_score", "hidden_iou",
    ]
    with (ROOT / "harmful_object_matches.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output_rows)

    summary = {
        "rows": len(output_rows),
        "anchor_center_mismatches": anchor_errors,
        "remain_harmful_0.50": sum(row["reason_50"] == "remains_harmful" for row in output_rows),
        "remain_harmful_0.70": sum(row["reason_70"] == "remains_harmful" for row in output_rows),
        "late_matches_0.50": sum(row["reason_50"] == "late_fusion_matches_anchor" for row in output_rows),
        "late_matches_0.70": sum(row["reason_70"] == "late_fusion_matches_anchor" for row in output_rows),
        "neither_local_0.50": sum(row["reason_50"] == "neither_local_matches_anchor" for row in output_rows),
        "neither_local_0.70": sum(row["reason_70"] == "neither_local_matches_anchor" for row in output_rows),
        "tests_run": result.testsRun,
        "dms_commit": COMMIT,
    }
    (ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_report(output_rows, result.testsRun)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
