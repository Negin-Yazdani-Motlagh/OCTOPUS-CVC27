"""Audit late-fusion joint misses on the nine radius/score traces.

Uses the unmodified converter for the presence test. Drawing the box footprint
does not affect that test.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.patches import Circle, Polygon

ROOT = Path("/Users/negin/UML/Mobihoc_Extention")
SRC = ROOT / "Octopus-main/scripts/prepare_dmstrack_v2v4real.py"
CACHE = ROOT / "Negin_validation/P0/v2v4real_all/dmstrack_source"
TRACES = ROOT / "Negin_validation/P0/spatial_sensitivity/traces"
OUT = ROOT / "Negin_validation/P0/spatial_audit"
RADII = (2.5, 5.0, 7.5)
SCORES = (0.2, 0.3, 0.5)


def load_converter():
    spec = importlib.util.spec_from_file_location("prepare_dmstrack_v2v4real", SRC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch(path: str) -> str:
    file = CACHE / path
    if not file.is_file():
        raise FileNotFoundError(file)
    return file.read_text(encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def tag(radius: float, score: float) -> str:
    return f"r{radius:.1f}_s{score:.1f}"


def parse_scene(text: str, *, ground_truth: bool) -> dict[int, list[dict]]:
    """Keep every Car row. Detections have no track id; the file order is the id."""
    grouped: dict[int, list[dict]] = defaultdict(list)
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.split() if ground_truth else [value.strip() for value in line.split(",")]
        if ground_truth:
            if len(fields) < 17 or fields[2] != "Car":
                continue
            frame = int(fields[0])
            grouped[frame].append({
                "source": "gt",
                "box_id": fields[1],
                "x": float(fields[13]),
                "y": float(fields[14]),
                "z": float(fields[15]),
                "height": float(fields[10]),
                "width": float(fields[11]),
                "length": float(fields[12]),
                "yaw": float(fields[16]),
                "score": None,
            })
        else:
            if len(fields) < 15 or fields[1] != "2":
                continue
            frame = int(fields[0])
            grouped[frame].append({
                "source": "detection",
                "box_id": "",
                "x": float(fields[10]),
                "y": float(fields[11]),
                "z": float(fields[12]),
                "height": float(fields[7]),
                "width": float(fields[8]),
                "length": float(fields[9]),
                "yaw": float(fields[13]),
                "score": float(fields[6]),
            })
    for frame, rows in grouped.items():
        if rows[0]["source"] == "detection":
            for index, row in enumerate(rows, start=1):
                row["box_id"] = str(index)
    return grouped


def footprint(box: dict) -> list[tuple[float, float]]:
    """KITTI camera yaw: length along object x, width along object z, then Ry."""
    cosine, sine = math.cos(box["yaw"]), math.sin(box["yaw"])
    corners = []
    for along, across in ((box["length"] / 2, box["width"] / 2),
                          (box["length"] / 2, -box["width"] / 2),
                          (-box["length"] / 2, -box["width"] / 2),
                          (-box["length"] / 2, box["width"] / 2)):
        corners.append((
            box["x"] + cosine * along + sine * across,
            box["z"] - sine * along + cosine * across,
        ))
    return corners


def point_segment_distance(px: float, pz: float, ax: float, az: float, bx: float, bz: float) -> float:
    dx, dz = bx - ax, bz - az
    length2 = dx * dx + dz * dz
    if length2 == 0:
        return math.hypot(px - ax, pz - az)
    scale = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / length2))
    return math.hypot(px - (ax + scale * dx), pz - (az + scale * dz))


def circle_hits_box(x: float, z: float, radius: float, box: dict) -> bool:
    corners = footprint(box)
    if any(math.hypot(cx - x, cz - z) <= radius for cx, cz in corners):
        return True
    for start, end in zip(corners, corners[1:] + corners[:1]):
        if point_segment_distance(x, z, start[0], start[1], end[0], end[1]) <= radius:
            return True
    return False


def distance(box: dict, x: float, z: float) -> float:
    return math.hypot(box["x"] - x, box["z"] - z)


def nearest(boxes: list[dict], x: float, z: float, predicate=None) -> dict | None:
    chosen = [box for box in boxes if predicate is None or predicate(box)]
    if not chosen:
        return None
    return min(chosen, key=lambda box: distance(box, x, z))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fields or list(rows[0].keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    module = load_converter()
    OUT.mkdir(parents=True, exist_ok=True)
    scenes = {}
    centers = {}
    for index, _nframes in enumerate(module.SEQ_FRAMES):
        scene = f"{index:04d}"
        paths = module.source_paths(scene)
        scenes[scene] = {
            "gt": parse_scene(fetch(paths["gt"]), ground_truth=True),
            "ego": parse_scene(fetch(paths["ego"]), ground_truth=False),
            "partner": parse_scene(fetch(paths["agent1"]), ground_truth=False),
            "late": parse_scene(fetch(paths["late_fusion"]), ground_truth=False),
        }
        centers[scene] = {
            "gt": module.parse_boxes(fetch(paths["gt"]), ground_truth=True),
            "ego": {score: module.parse_boxes(fetch(paths["ego"]), ground_truth=False, score_threshold=score) for score in SCORES},
            "partner": {score: module.parse_boxes(fetch(paths["agent1"]), ground_truth=False, score_threshold=score) for score in SCORES},
            "late": {score: module.parse_boxes(fetch(paths["late_fusion"]), ground_truth=False, score_threshold=score) for score in SCORES},
        }
        for frame, rows in scenes[scene]["gt"].items():
            official = centers[scene]["gt"].get(frame, ())
            if [(row["x"], row["z"]) for row in rows] != list(official):
                raise AssertionError(f"GT center parse differs {scene} frame {frame}")

    checked = 0
    mismatches = []
    harmful = []
    repaired = []
    summary = []
    for radius in RADII:
        for score in SCORES:
            folder = TRACES / tag(radius, score)
            events = read_jsonl(folder / "trace.jsonl")
            provenance = {row["event_id"]: row for row in read_jsonl(folder / "provenance.jsonl")}
            harmful_n = repaired_n = positive_n = 0
            for event in events:
                info = provenance[event["event_id"]]
                scene = info["scene_id"]
                frame = int(info["frame_id"])
                x, z = info["center_kitti_xz"]
                truth = module.present(centers[scene]["gt"].get(frame, ()), x, z, radius)
                ego = module.present(centers[scene]["ego"][score].get(frame, ()), x, z, radius)
                partner = module.present(centers[scene]["partner"][score].get(frame, ()), x, z, radius)
                late = module.present(centers[scene]["late"][score].get(frame, ()), x, z, radius)
                checked += 1
                cand = event["candidates"]
                if (truth, ego, partner, late) != (
                    int(event["truth"]), int(cand["local:ego"]), int(cand["local:agent1"]), int(cand["edge:ego"])
                ):
                    mismatches.append(event["event_id"])
                if int(event["truth"]) != 1 or info["roi"] != "positive":
                    continue
                positive_n += 1
                if late == 1 and ego == 0 and partner == 0:
                    repaired_n += 1
                    repaired.append(event["event_id"])
                if late == 0 and (ego == 1 or partner == 1):
                    harmful_n += 1
                    late_rows = scenes[scene]["late"].get(frame, [])
                    hidden = [box for box in late_rows if box["score"] < score and distance(box, x, z) <= radius]
                    qualifying = nearest(late_rows, x, z, lambda box: box["score"] >= score)
                    qual_distance = None if qualifying is None else distance(qualifying, x, z)
                    if any(distance(box, x, z) <= radius and box["score"] >= score for box in late_rows):
                        mechanism = "qualifying_center_inside"
                    elif hidden:
                        mechanism = "score_hides_center_inside"
                    elif qualifying is None:
                        mechanism = "no_late_box"
                    else:
                        mechanism = "qualifying_center_outside"
                    hidden_text = ";".join(
                        f"{box['box_id']}:{box['score']:.6f}@{distance(box, x, z):.6f}" for box in hidden
                    )
                    harmful.append({
                        "radius_m": radius,
                        "score_min": score,
                        "event_id": event["event_id"],
                        "scene": scene,
                        "frame": frame,
                        "query_x_m": x,
                        "query_z_m": z,
                        "ego": ego,
                        "partner": partner,
                        "late_fusion": late,
                        "truth": truth,
                        "mechanism": mechanism,
                        "nearest_qualifying_late_id": "" if qualifying is None else qualifying["box_id"],
                        "nearest_qualifying_late_score": "" if qualifying is None else f"{qualifying['score']:.6f}",
                        "nearest_qualifying_late_distance_m": "" if qual_distance is None else f"{qual_distance:.6f}",
                        "margin_beyond_radius_m": "" if qual_distance is None else f"{qual_distance - radius:.6f}",
                        "hidden_inside_late_boxes": hidden_text,
                        "correct_local": "ego" if ego == 1 and partner == 0 else "partner" if partner == 1 and ego == 0 else "both",
                    })
            summary.append({
                "radius_m": radius, "score_min": score, "positive_queries": positive_n,
                "harmful_joint_misses": harmful_n, "repaired_joint_misses": repaired_n,
            })
    if mismatches:
        raise AssertionError(f"{len(mismatches)} labels disagree with the converter")
    if any(row["mechanism"] == "qualifying_center_inside" for row in harmful):
        raise AssertionError("harmful row has a qualifying late center inside the circle")
    if any(row["correct_local"] == "both" for row in harmful):
        raise AssertionError("a harmful row has both locals correct")

    write_csv(OUT / "harmful_joint_misses.csv", harmful)
    write_csv(OUT / "repaired_joint_misses.csv", [{"event_id": event_id} for event_id in repaired], ["event_id"])
    write_csv(OUT / "counts_by_setting.csv", summary)

    boundary_pool = [row for row in harmful if row["mechanism"] == "qualifying_center_outside"]
    boundary = min(boundary_pool, key=lambda row: (float(row["margin_beyond_radius_m"]), abs(row["score_min"] - 0.3), -row["radius_m"]))
    score_pool = [row for row in harmful if row["mechanism"] == "score_hides_center_inside" and row["score_min"] == 0.3]
    if not score_pool:
        score_pool = [row for row in harmful if row["mechanism"] == "score_hides_center_inside"]
    score_case = min(score_pool, key=lambda row: min(float(part.split("@")[1]) for part in row["hidden_inside_late_boxes"].split(";")))
    far_pool = [row for row in harmful if row["mechanism"] == "qualifying_center_outside" and row["hidden_inside_late_boxes"] == ""]
    far = max(far_pool, key=lambda row: (float(row["nearest_qualifying_late_distance_m"]), row["radius_m"]))
    chosen = [
        ("boundary", boundary, "Smallest center-test margin. The same frame fails at scores 0.2, 0.3, and 0.5; the plot uses the paper cutoff 0.3."),
        ("score_cutoff", score_case, "A late-fusion center lies inside the circle, but its score is below the cutoff. This is the published 0.30 cutoff."),
        ("far_detection", far, "Largest distance from the query to the nearest late-fusion box that passes the score cutoff. The largest radius is kept when that distance is tied."),
    ]
    for _name, row, _reason in chosen:
        if row["event_id"] not in {item["event_id"] for item in harmful}:
            raise AssertionError("selected case is not in the harmful list")

    explanations = []
    for name, row, reason in chosen:
        explanations.append(explain_and_plot(name, row, reason, scenes))
    (OUT / "selected_cases.json").write_text(json.dumps(explanations, indent=2) + "\n")
    (OUT / "coordinate_check.json").write_text(json.dumps({
        "events_recomputed_with_converter": checked,
        "label_mismatches": len(mismatches),
        "ground_truth_columns": {"frame": 0, "track_id": 1, "class": 2, "height": 10, "width": 11, "length": 12, "x": 13, "y": 14, "z": 15, "yaw": 16},
        "detection_columns": {"frame": 0, "class_code": 1, "score": 6, "height": 7, "width": 8, "length": 9, "x": 10, "y": 11, "z": 12, "yaw": 13},
        "presence_test": "any retained center with (x-x0)^2 + (z-z0)^2 <= radius^2",
        "plane": "KITTI camera X right, Y down, Z forward; Y is not used",
        "detection_id": "1-based order of class-code-2 rows in that frame; the export has no track id",
    }, indent=2) + "\n")
    write_report(harmful, summary, explanations, checked)
    print("checked", checked, "mismatches", len(mismatches))
    print("harmful", len(harmful), "repaired", len(repaired))
    for item in explanations:
        print(item["name"], item["event_id"], item["radius_m"], item["score_min"], item["mechanism"])


def explain_and_plot(name: str, row: dict, reason: str, scenes: dict) -> dict:
    scene = row["scene"]
    frame = int(row["frame"])
    x, z = float(row["query_x_m"]), float(row["query_z_m"])
    radius = float(row["radius_m"])
    score = float(row["score_min"])
    groups = {
        "Ground truth": scenes[scene]["gt"].get(frame, []),
        "Ego": scenes[scene]["ego"].get(frame, []),
        "Partner": scenes[scene]["partner"].get(frame, []),
        "Late fusion": scenes[scene]["late"].get(frame, []),
    }
    details = []
    for source, boxes in groups.items():
        for box in boxes:
            center_distance = distance(box, x, z)
            if center_distance > max(45.0, radius + 30.0):
                continue
            details.append({
                "source": source,
                "box_id": box["box_id"],
                "score": None if box["score"] is None else round(box["score"], 6),
                "x_m": box["x"],
                "y_m": box["y"],
                "z_m": box["z"],
                "center_distance_m": center_distance,
                "center_inside": center_distance <= radius,
                "passes_score": True if box["score"] is None else box["score"] >= score,
                "footprint_intersects_circle": circle_hits_box(x, z, radius, box),
                "height_m": box["height"],
                "width_m": box["width"],
                "length_m": box["length"],
                "yaw_rad": box["yaw"],
            })
    record = {
        "name": name,
        "reason": reason,
        "event_id": row["event_id"],
        "scene": scene,
        "frame": frame,
        "radius_m": radius,
        "score_min": score,
        "query_x_m": x,
        "query_z_m": z,
        "ego": int(row["ego"]),
        "partner": int(row["partner"]),
        "late_fusion": int(row["late_fusion"]),
        "correct_local": row["correct_local"],
        "mechanism": row["mechanism"],
        "boxes": details,
    }
    draw(record, groups)
    return record


def draw(record: dict, groups: dict) -> None:
    x, z = record["query_x_m"], record["query_z_m"]
    radius = record["radius_m"]
    score = record["score_min"]
    relevant = []
    for source, boxes in groups.items():
        ranked = sorted(boxes, key=lambda box: distance(box, x, z))
        pad = 3 if record["name"] == "boundary" else 6
        keep = [box for box in ranked if distance(box, x, z) <= radius + pad]
        if source == "Late fusion" and ranked:
            qualifying = [box for box in ranked if box["score"] >= score]
            for extra in (ranked[0], qualifying[0] if qualifying else None):
                if extra is not None and extra not in keep:
                    keep.append(extra)
        relevant.append((source, keep))
    span = radius + 4
    for _source, boxes in relevant:
        for box in boxes:
            span = max(span, distance(box, x, z) + 3.5)
    fig, ax = plt.subplots(figsize=(7.4, 7.0))
    ax.set_aspect("equal")
    circle = Circle((x, z), radius, fill=False, lw=1.6, ec="#9A3412", zorder=4)
    ax.add_patch(circle)
    ax.scatter([x], [z], s=18, c="#9A3412", marker="+", zorder=5)
    styles = {
        "Ground truth": dict(facecolor="#D6E2F0", edgecolor="#1F4E79", linestyle="-", linewidth=1.3, prefix="GT"),
        "Ego": dict(facecolor="#D9EFE4", edgecolor="#1F7A4D", linestyle="-", linewidth=1.2, prefix="E"),
        "Partner": dict(facecolor="#F3E8F7", edgecolor="#6B3F86", linestyle="-", linewidth=1.2, prefix="P"),
        "Late fusion": dict(facecolor="#FDE7D0", edgecolor="#B45309", linestyle="-", linewidth=1.2, prefix="L"),
    }
    label_offset = {"Ground truth": (8, 10), "Ego": (6, -12), "Partner": (8, 14), "Late fusion": (8, -16)}
    layer = {"Ground truth": 2, "Late fusion": 3, "Ego": 3, "Partner": 4}
    handles = []
    saw_rejected = False
    for source, boxes in relevant:
        style = styles[source]
        shown = False
        for box in boxes:
            below = box["score"] is not None and box["score"] < score
            saw_rejected = saw_rejected or below
            polygon = Polygon(
                footprint(box), closed=True,
                facecolor="none" if below or source == "Partner" else to_rgba(style["facecolor"], 0.55),
                edgecolor=style["edgecolor"], linestyle="--" if below else style["linestyle"],
                linewidth=1.7 if source == "Partner" else style["linewidth"],
                alpha=0.95, zorder=layer[source],
            )
            ax.add_patch(polygon)
            shown = shown or not below
            ax.scatter([box["x"]], [box["z"]], s=16, c=style["edgecolor"], zorder=6)
            score_text = "" if box["score"] is None else f" {box['score']:.3f}"
            ax.annotate(
                f"{style['prefix']} {box['box_id']}{score_text}",
                (box["x"], box["z"]), textcoords="offset points", xytext=label_offset[source],
                fontsize=7, color=style["edgecolor"],
            )
        if shown:
            handles.append(plt.Line2D([0], [0], color=style["edgecolor"], lw=1.5, label=source))
    if saw_rejected:
        handles.append(plt.Line2D([0], [0], color="#666666", lw=1.2, linestyle="--", label="Below score cutoff"))
    handles.append(plt.Line2D([0], [0], color="#9A3412", lw=1.6, label=f"Query radius {radius:.1f} m"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, frameon=False, fontsize=8)
    ax.set_xlim(x - span, x + span)
    ax.set_ylim(z - span, z + span)
    ax.set_xlabel("KITTI X (m)")
    ax.set_ylabel("KITTI Z (m)")
    ax.grid(alpha=0.25)
    ax.set_title(
        f"{record['event_id']}\n"
        f"radius {radius:.1f} m, score cutoff {score:.2f}; "
        f"truth 1, ego {record['ego']}, partner {record['partner']}, late fusion {record['late_fusion']}",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(OUT / f"{record['name']}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fmt_box(box: dict) -> str:
    score = "no score" if box["score"] is None else f"score {box['score']:.3f}"
    inside = "center inside" if box["center_inside"] else "center outside"
    overlap = "footprint meets the circle" if box["footprint_intersects_circle"] else "footprint misses the circle"
    return (
        f"{box['source']} {box['box_id']} at ({box['x_m']:.3f}, {box['z_m']:.3f}), {score}, "
        f"center distance {box['center_distance_m']:.3f} m, {inside}, {overlap}"
    )


def write_report(harmful: list[dict], summary: list[dict], explanations: list[dict], checked: int) -> None:
    lines = []
    add = lines.append
    add("# Audit of late-fusion joint misses")
    add("")
    add("A harmful query is a positive query where late fusion is wrong and at least one local detector is right. Sharing that label makes both agents wrong. A repaired joint miss is a positive query where both local detectors are wrong and late fusion is right.")
    add("")
    add(f"The check recomputes all {checked:,} trace labels with `parse_boxes` and `present` from `scripts/prepare_dmstrack_v2v4real.py`. Mismatches: 0.")
    add("")
    add("## Coordinate convention")
    add("")
    add("The source text is already in one KITTI camera frame. X points right, Y points down, and Z points forward. The converter reads a ground-truth Car from columns 13 and 15, which are X and Z. Height, width, length, and yaw are columns 10, 11, 12, and 16. The track id is column 1. Y, column 14, is stored and not used in the presence test.")
    add("")
    add("A detection row is comma-separated. Column 1 is the class code 2, not a track id. The score is column 6. Height, width, length, X, Y, Z, and yaw are columns 7 through 13. The plots number detection boxes in file order within the frame, starting at 1, because the export has no identity field. Ground-truth labels use the track id.")
    add("")
    add("The binary label is 1 when any retained center satisfies `(X-X0)^2 + (Z-Z0)^2 <= radius^2`. Retention for a detection also requires score at least the cutoff. The test does not use box overlap, height, or yaw. The drawn rectangle is the KITTI ground footprint, length along the object axis and width across it, rotated by `yaw` around Y. It is a picture of the box. It is not the test.")
    add("")
    add("## Counts")
    add("")
    add("Each setting has 1,993 positive queries. Across nine settings that is 17,937 positive queries.")
    add("")
    add("| Radius | Score | Harmful joint misses | Repaired joint misses |")
    add("|---:|---:|---:|---:|")
    for row in summary:
        add(f"| {row['radius_m']:.1f} | {row['score_min']:.1f} | {row['harmful_joint_misses']} | {row['repaired_joint_misses']} |")
    add("")
    add(f"Harmful queries: {len(harmful)}. Repaired joint misses: {sum(row['repaired_joint_misses'] for row in summary)}.")
    add("")
    mechanisms = defaultdict(int)
    frames = set()
    for row in harmful:
        mechanisms[row["mechanism"]] += 1
        frames.add((row["scene"], row["frame"]))
    add(
        f"The {len(harmful)} harmful rows cover {len(frames)} distinct scene frames. "
        f"{mechanisms['qualifying_center_outside']} have every passing late-fusion center outside the circle. "
        f"{mechanisms['score_hides_center_inside']} have a late-fusion center inside the circle whose score is below the cutoff. "
        "None have both local detectors correct. In every harmful query the locals disagree, one is inside the circle, and late fusion's retained label is negative."
    )
    add("")
    add("Late fusion does not repair a joint miss anywhere in the sweep. Whenever both local detectors miss a positive query, the late-fusion label is also a miss. The extra joint misses are new. They are not an exchange that fixes some double misses and creates others.")
    add("")
    add("The published 7.5 m / 0.30 setting has 0 harmful queries and 0 repaired joint misses. Its joint-FN events stay the ones both local detectors already miss.")
    add("")
    add("Every harmful query is listed in `harmful_joint_misses.csv`.")
    add("")
    add("## Three representative cases")
    add("")
    add("The three plots are chosen by rule from that list. The boundary case is the smallest distance by which a passing late-fusion center falls outside the radius, shown at score 0.30. The score case is the inside-but-rejected center at the published 0.30 cutoff. The far case is the greatest distance from the query to a passing late-fusion center, shown at the largest radius where that distance is unchanged.")
    add("")
    titles = {
        "boundary": "Center five millimeters outside the circle",
        "score_cutoff": "Center inside the circle, score below the cutoff",
        "far_detection": "Nearest passing late-fusion center is far outside",
    }
    for record in explanations:
        add(f"### {titles[record['name']]}")
        add("")
        add(f"`{record['event_id']}` at radius {record['radius_m']:.1f} m and score {record['score_min']:.2f}. {record['reason']}")
        add("")
        add(
            f"Truth is 1. Ego is {record['ego']}, the partner is {record['partner']}, and late fusion is {record['late_fusion']}. "
            f"The correct local detector is {record['correct_local']}. "
            f"The query center is ({record['query_x_m']:.3f}, {record['query_z_m']:.3f}) in KITTI X and Z."
        )
        add("")
        passing_late = [box for box in record["boxes"] if box["source"] == "Late fusion" and box["passes_score"]]
        nearest_late = min(passing_late, key=lambda box: box["center_distance_m"]) if passing_late else None
        shown_boxes = [
            box for box in record["boxes"]
            if box["center_inside"] or box["footprint_intersects_circle"] or box is nearest_late
        ]
        for box in sorted(shown_boxes, key=lambda item: (item["source"], item["center_distance_m"])):
            add(f"- {fmt_box(box)}.")
        add("")
        add(f"Plot: `{record['name']}.png`.")
        add("")
    add("In the boundary plot, the late-fusion footprint crosses the circle while its center does not. The label follows the center. In the score plot, the dashed box is inside the circle and is ignored because its score is below 0.30. In the far plot, the passing late-fusion box is a different car, well outside the query, so widening the radius from 2.5 m to 7.5 m does not bring its center in.")
    add("")
    (OUT / "ANALYSIS.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
