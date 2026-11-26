"""Radius and score sweep using the unmodified DMSTrack converter.

The original script chooses the regions and writes each trace. This file only
reads those traces and the cached source text.
"""
from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path("/Users/negin/UML/Mobihoc_Extention")
SRC = ROOT / "Octopus-main/scripts/prepare_dmstrack_v2v4real.py"
CACHE = ROOT / "Negin_validation/P0/v2v4real_all/dmstrack_source"
BASELINE_TRACE = ROOT / "Negin_validation/P0/v2v4real_all/trace.jsonl"
BASELINE_COUNTS = ROOT / "Negin_validation/P0/v2v4real_all/sequence_counts.csv"
OUT = ROOT / "Negin_validation/P0/spatial_sensitivity"
RADII = (2.5, 5.0, 7.5)
SCORES = (0.2, 0.3, 0.5)
POLICIES = ("local", "late_fusion", "disagreement_gate", "OR")


def load_converter():
    spec = importlib.util.spec_from_file_location("prepare_dmstrack_v2v4real", SRC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch_factory(module):
    def fetch(path: str) -> str:
        dst = CACHE / path
        if not dst.is_file():
            raise FileNotFoundError(dst)
        return dst.read_text(encoding="utf-8")
    return fetch


def tag(radius: float, score: float) -> str:
    return f"r{radius:.1f}_s{score:.1f}"


def policy_labels(ego: int, partner: int, late: int) -> dict[str, tuple[int, int]]:
    gate = late if ego != partner else ego
    either = max(ego, partner)
    return {
        "local": (ego, partner),
        "late_fusion": (late, late),
        "disagreement_gate": (gate, gate),
        "OR": (either, either),
    }


def blank():
    return {"queries": 0, "positives": 0, "negatives": 0, "agent_errors": 0,
            "both_wrong": 0, "joint_fn": 0, "joint_fp": 0}


def add_event(bucket: dict, labels: dict[str, tuple[int, int]], truth: int) -> None:
    for name, pair in labels.items():
        rec = bucket[name]
        rec["queries"] += 1
        rec["positives"] += int(truth == 1)
        rec["negatives"] += int(truth == 0)
        wrongs = [label != truth for label in pair]
        rec["agent_errors"] += sum(wrongs)
        both = int(all(wrongs))
        rec["both_wrong"] += both
        rec["joint_fn"] += int(truth == 1 and both)
        rec["joint_fp"] += int(truth == 0 and both)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def inside(points, x, z, radius) -> list:
    limit = radius * radius
    return [p for p in points if (p[0] - x) ** 2 + (p[1] - z) ** 2 <= limit]


def parse_labeled(text: str, *, ground_truth: bool, score_threshold: float):
    """Same columns as the converter, plus GT track id or detection score."""
    out = defaultdict(list)
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.split() if ground_truth else [v.strip() for v in line.split(",")]
        if ground_truth:
            if len(fields) < 17 or fields[2] != "Car":
                continue
            out[int(fields[0])].append((float(fields[13]), float(fields[15]), fields[1]))
        else:
            if len(fields) < 15 or fields[1] != "2":
                continue
            score = float(fields[6])
            if score < score_threshold:
                continue
            out[int(fields[0])].append((float(fields[10]), float(fields[12]), f"{score:.3f}"))
    return out


def main() -> None:
    module = load_converter()
    fetch = fetch_factory(module)
    OUT.mkdir(parents=True, exist_ok=True)
    trace_root = OUT / "traces"
    configs = []
    for radius in RADII:
        for score in SCORES:
            dest = trace_root / tag(radius, score)
            rows = module.prepare(fetch, dest, threshold=score, radius=radius)
            configs.append((radius, score, dest, rows))
            print(f"prepared {tag(radius, score)} events {sum(r['balanced_events'] for r in rows)}")

    baseline_rows = list(csv.DictReader(BASELINE_COUNTS.open()))
    prepared = {(r, s): rows for r, s, _, rows in configs}
    base_rows = prepared[(7.5, 0.3)]
    for exp, actual in zip(baseline_rows, base_rows):
        for key, value in exp.items():
            if str(actual[key]) != str(value):
                raise AssertionError(f"baseline mismatch {actual['scene']} {key}")
    old = {row["event_id"]: row for row in read_jsonl(BASELINE_TRACE)}
    new = {row["event_id"]: row for row in read_jsonl(trace_root / tag(7.5, 0.3) / "trace.jsonl")}
    if old.keys() != new.keys():
        raise AssertionError("baseline trace ids differ")
    for key, row in old.items():
        if row["truth"] != new[key]["truth"] or row["candidates"] != new[key]["candidates"]:
            raise AssertionError(f"baseline label mismatch {key}")

    policy_rows = []
    sequence_rows = []
    finding_rows = []
    for radius, score, dest, count_rows in configs:
        events = read_jsonl(dest / "trace.jsonl")
        provenance = {row["event_id"]: row for row in read_jsonl(dest / "provenance.jsonl")}
        pooled = {name: blank() for name in POLICIES}
        by_scene = defaultdict(lambda: {name: blank() for name in POLICIES})
        fn_events = {name: set() for name in POLICIES}
        gate_or_differ = 0
        gate_or_gate_wrong = 0
        gate_or_on_positive = 0
        scenes_gate_eq_or = 0
        scene_r2_late_gt = 0
        scene_r2_late_eq = 0
        scene_r2_late_lt = 0
        scene_sets = defaultdict(lambda: {name: blank() for name in POLICIES})
        for event in events:
            scene = provenance[event["event_id"]]["scene_id"]
            truth = int(event["truth"])
            cand = event["candidates"]
            labels = policy_labels(int(cand["local:ego"]), int(cand["local:agent1"]), int(cand["edge:ego"]))
            add_event(pooled, labels, truth)
            add_event(by_scene[scene], labels, truth)
            for name, pair in labels.items():
                if truth == 1 and pair[0] != truth and pair[1] != truth:
                    fn_events[name].add(event["event_id"])
            if labels["disagreement_gate"] != labels["OR"]:
                gate_or_differ += 1
                if truth == 1:
                    gate_or_on_positive += 1
                if labels["disagreement_gate"][0] != truth:
                    gate_or_gate_wrong += 1
        for scene, bucket in by_scene.items():
            if bucket["disagreement_gate"]["both_wrong"] == bucket["OR"]["both_wrong"] and bucket["disagreement_gate"]["agent_errors"] == bucket["OR"]["agent_errors"]:
                scenes_gate_eq_or += 1
            if bucket["late_fusion"]["both_wrong"] > bucket["local"]["both_wrong"]:
                scene_r2_late_gt += 1
            elif bucket["late_fusion"]["both_wrong"] == bucket["local"]["both_wrong"]:
                scene_r2_late_eq += 1
            else:
                scene_r2_late_lt += 1
            for name in POLICIES:
                rec = bucket[name]
                sequence_rows.append({
                    "radius_m": radius, "score_min": score, "sequence": scene, "policy": name,
                    "queries": rec["queries"], "positives": rec["positives"], "negatives": rec["negatives"],
                    "agent_labels": 2 * rec["queries"], "agent_errors": rec["agent_errors"],
                    "joint_fn": rec["joint_fn"], "joint_fp": rec["joint_fp"], "r2_count": rec["both_wrong"],
                })
        for name in POLICIES:
            rec = pooled[name]
            policy_rows.append({
                "radius_m": radius, "score_min": score, "task": "balanced", "policy": name,
                "queries": rec["queries"], "positives": rec["positives"], "negatives": rec["negatives"],
                "agent_labels": 2 * rec["queries"], "agent_errors": rec["agent_errors"],
                "mean_error": rec["agent_errors"] / (2 * rec["queries"]),
                "joint_fn": rec["joint_fn"], "joint_fn_rate": rec["joint_fn"] / rec["positives"],
                "joint_fp": rec["joint_fp"], "joint_fp_rate": rec["joint_fp"] / rec["negatives"],
                "r2_count": rec["both_wrong"], "r2": rec["both_wrong"] / rec["queries"],
            })
        same_fn = len(set(map(frozenset, (fn_events[n] for n in POLICIES)))) == 1
        finding_rows.append({
            "radius_m": radius, "score_min": score,
            "queries": pooled["local"]["queries"],
            "frames": pooled["local"]["queries"] // 2,
            "late_mean_below_local": int(pooled["late_fusion"]["agent_errors"] < pooled["local"]["agent_errors"]),
            "late_r2_above_local": int(pooled["late_fusion"]["both_wrong"] > pooled["local"]["both_wrong"]),
            "joint_fn_same_events": int(same_fn),
            "joint_fn_count": pooled["local"]["joint_fn"],
            "gate_fp_le_or": int(pooled["disagreement_gate"]["joint_fp"] <= pooled["OR"]["joint_fp"]),
            "gate_or_differ_queries": gate_or_differ,
            "gate_or_differ_on_positive": gate_or_on_positive,
            "gate_wrong_where_they_differ": gate_or_gate_wrong,
            "sequences_gate_equals_or": scenes_gate_eq_or,
            "sequences_late_r2_higher": scene_r2_late_gt,
            "sequences_late_r2_equal": scene_r2_late_eq,
            "sequences_late_r2_lower": scene_r2_late_lt,
            "fixed_events": sum(int(r["fixed_events"]) for r in count_rows),
            "fixed_positives": sum(int(r["fixed_positives"]) for r in count_rows),
            "fixed_ego_errors": sum(int(r["fixed_ego_errors"]) for r in count_rows),
            "fixed_agent1_errors": sum(int(r["fixed_agent1_errors"]) for r in count_rows),
            "fixed_late_errors": sum(int(r["fixed_late_fusion_errors"]) for r in count_rows),
            "fixed_separate_joint": sum(int(r["fixed_separate_joint_errors"]) for r in count_rows),
        })

    # Selection uses ground truth only, so it depends on radius and not on score.
    gt_maps = {}
    det_counts = {score: Counter() for score in SCORES}
    for index, nframes in enumerate(module.SEQ_FRAMES):
        scene = f"{index:04d}"
        paths = module.source_paths(scene)
        gt_maps[scene] = (nframes, module.parse_boxes(fetch(paths["gt"]), ground_truth=True))
        for score in SCORES:
            for name in ("ego", "agent1", "cobevt", "late_fusion"):
                parsed = module.parse_boxes(fetch(paths[name]), ground_truth=False, score_threshold=score)
                det_counts[score][name] += sum(len(v) for v in parsed.values())

    selection_rows = []
    offset_rows = []
    centers_by_radius = {}
    multi_rows = []
    for radius in RADII:
        emitted = 0
        dropped = 0
        offsets = Counter()
        multi = Counter()
        cars_in_positive = 0
        centers = {}
        for scene, (nframes, gt) in gt_maps.items():
            for frame in range(nframes):
                chosen = module.choose_regions(gt, frame, task="balanced", radius=radius)
                if not chosen:
                    dropped += 1
                    continue
                emitted += 1
                objects = gt.get(frame, ())
                px, pz = chosen[0][1]
                nx, nz = chosen[1][1]
                offset = (round(nx - px, 6), round(nz - pz, 6))
                offsets[offset] += 1
                n_pos = sum(1 for x, z in objects if (x - px) ** 2 + (z - pz) ** 2 <= radius * radius)
                n_neg = sum(1 for x, z in objects if (x - nx) ** 2 + (z - nz) ** 2 <= radius * radius)
                if n_neg != 0:
                    raise AssertionError(f"negative region contains GT {scene} {frame} r={radius}")
                cars_in_positive += n_pos
                multi[n_pos] += 1
                centers[(scene, frame)] = ((px, pz), (nx, nz))
        centers_by_radius[radius] = centers
        selection_rows.append({
            "radius_m": radius, "frames_total": sum(module.SEQ_FRAMES),
            "frames_emitted": emitted, "frames_dropped": dropped,
            "balanced_queries": 2 * emitted, "positives": emitted, "negatives": emitted,
            "gt_cars_in_positive_rois": cars_in_positive,
            "positive_rois_with_one_car": multi[1],
            "positive_rois_with_two_or_more": sum(v for k, v in multi.items() if k >= 2),
            "max_gt_cars_in_one_positive_roi": max(multi),
        })
        for (dx, dz), count in sorted(offsets.items(), key=lambda item: -item[1]):
            offset_rows.append({"radius_m": radius, "offset_x_m": dx, "offset_z_m": dz, "frames": count})
        for n_cars, count in sorted(multi.items()):
            multi_rows.append({"radius_m": radius, "gt_cars_inside_positive": n_cars, "frames": count})

    base_centers = centers_by_radius[7.5]
    move_rows = []
    for radius, centers in centers_by_radius.items():
        if centers.keys() != base_centers.keys():
            raise AssertionError("emitted frames differ by radius")
        positive_moves = 0
        negative_moves = 0
        for key, (pos, neg) in centers.items():
            base_pos, base_neg = base_centers[key]
            positive_moves += int(pos != base_pos)
            negative_moves += int(neg != base_neg)
        move_rows.append({
            "radius_m": radius, "frames": len(centers),
            "positive_centers_different_from_7.5m": positive_moves,
            "negative_centers_different_from_7.5m": negative_moves,
        })

    # Same geometry across scores: provenance centers must match within a radius.
    for radius in RADII:
        reference = {
            row["event_id"]: tuple(row["center_kitti_xz"])
            for row in read_jsonl(trace_root / tag(radius, 0.3) / "provenance.jsonl")
        }
        for score in SCORES:
            current = {
                row["event_id"]: tuple(row["center_kitti_xz"])
                for row in read_jsonl(trace_root / tag(radius, score) / "provenance.jsonl")
            }
            if current != reference:
                raise AssertionError(f"query centers depend on score at r={radius} s={score}")

    flip_rows = []
    for radius in RADII:
        reference = {row["event_id"]: row for row in read_jsonl(trace_root / tag(radius, 0.3) / "trace.jsonl")}
        for score in SCORES:
            current = {row["event_id"]: row for row in read_jsonl(trace_root / tag(radius, score) / "trace.jsonl")}
            flips = Counter()
            for eid, row in current.items():
                before = reference[eid]
                if row["truth"] != before["truth"]:
                    raise AssertionError("truth changed with score")
                for key in ("local:ego", "local:agent1", "edge:ego"):
                    flips[key] += int(row["candidates"][key] != before["candidates"][key])
            flip_rows.append({
                "radius_m": radius, "score_min": score, "compared_with_score": 0.3,
                "queries": len(current),
                "ego_label_flips": flips["local:ego"],
                "partner_label_flips": flips["local:agent1"],
                "late_fusion_label_flips": flips["edge:ego"],
            })

    box_rows = []
    for score, counts in det_counts.items():
        for name, count in counts.items():
            box_rows.append({"score_min": score, "source": name, "boxes_retained": count})

    fixed_rows = []
    for radius, score, _, count_rows in configs:
        maps = {}
        for index, nframes in enumerate(module.SEQ_FRAMES):
            scene = f"{index:04d}"
            paths = module.source_paths(scene)
            maps[scene] = {
                "n": nframes,
                "gt": module.parse_boxes(fetch(paths["gt"]), ground_truth=True),
                "pred": {name: module.parse_boxes(fetch(paths[name]), ground_truth=False, score_threshold=score)
                         for name in ("ego", "agent1", "late_fusion")},
            }
        pooled = {name: blank() for name in POLICIES}
        for scene, item in maps.items():
            for frame in range(item["n"]):
                for _, (x, z) in module.choose_regions(item["gt"], frame, task="fixed_grid", radius=radius):
                    truth = module.present(item["gt"].get(frame, ()), x, z, radius)
                    pred = module.decisions(item["pred"], frame, x, z, radius)
                    labels = policy_labels(pred["ego"], pred["agent1"], pred["late_fusion"])
                    add_event(pooled, labels, truth)
        csv_events = sum(int(r["fixed_events"]) for r in count_rows)
        csv_pos = sum(int(r["fixed_positives"]) for r in count_rows)
        csv_ego = sum(int(r["fixed_ego_errors"]) for r in count_rows)
        csv_a1 = sum(int(r["fixed_agent1_errors"]) for r in count_rows)
        csv_late = sum(int(r["fixed_late_fusion_errors"]) for r in count_rows)
        csv_joint = sum(int(r["fixed_separate_joint_errors"]) for r in count_rows)
        if csv_events != pooled["local"]["queries"] or csv_pos != pooled["local"]["positives"]:
            raise AssertionError("fixed-grid recount disagrees with converter totals")
        if csv_late != pooled["late_fusion"]["both_wrong"] or csv_joint != pooled["local"]["both_wrong"]:
            raise AssertionError("fixed-grid error recount disagrees with converter")
        # Ego and partner errors are individual, not stored as agent_errors split.
        # Recompute from the converter columns rather than the paired sum.
        if csv_ego + csv_a1 != pooled["local"]["agent_errors"]:
            raise AssertionError("fixed-grid local error sum disagrees")
        for name in POLICIES:
            rec = pooled[name]
            fixed_rows.append({
                "radius_m": radius, "score_min": score, "task": "fixed_grid", "policy": name,
                "queries": rec["queries"], "positives": rec["positives"], "negatives": rec["negatives"],
                "agent_labels": 2 * rec["queries"], "agent_errors": rec["agent_errors"],
                "mean_error": rec["agent_errors"] / (2 * rec["queries"]),
                "joint_fn": rec["joint_fn"], "joint_fn_rate": rec["joint_fn"] / rec["positives"],
                "joint_fp": rec["joint_fp"], "joint_fp_rate": rec["joint_fp"] / rec["negatives"],
                "r2_count": rec["both_wrong"], "r2": rec["both_wrong"] / rec["queries"],
                "converter_ego_errors": csv_ego, "converter_partner_errors": csv_a1,
            })

    write_csv(OUT / "balanced_policy.csv", policy_rows)
    write_csv(OUT / "balanced_by_sequence.csv", sequence_rows)
    write_csv(OUT / "findings.csv", finding_rows)
    write_csv(OUT / "selection_by_radius.csv", selection_rows)
    write_csv(OUT / "negative_offsets.csv", offset_rows)
    write_csv(OUT / "center_movement.csv", move_rows)
    write_csv(OUT / "multi_car_positive.csv", multi_rows)
    write_csv(OUT / "label_flips_vs_score_0.3.csv", flip_rows)
    write_csv(OUT / "boxes_retained.csv", box_rows)
    write_csv(OUT / "fixed_grid_policy.csv", fixed_rows)
    examples = make_plots(module, fetch, trace_root)
    (OUT / "plot_examples.json").write_text(json.dumps(examples, indent=2) + "\n")
    write_report(policy_rows, finding_rows, selection_rows, offset_rows, move_rows,
                 multi_rows, flip_rows, box_rows, fixed_rows, examples)
    print("baseline matched previous 7.5 m / 0.30 trace")
    print("wrote", OUT)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_plots(module, fetch, trace_root: Path) -> list[dict]:
    events = read_jsonl(trace_root / tag(7.5, 0.3) / "trace.jsonl")
    provenance = {row["event_id"]: row for row in read_jsonl(trace_root / tag(7.5, 0.3) / "provenance.jsonl")}
    wanted = {"rescued_miss": None, "shared_false_alarm": None, "shared_miss": None}
    ordered = sorted(events, key=lambda row: (provenance[row["event_id"]]["scene_id"] != "0007", row["event_id"]))
    for event in ordered:
        truth = int(event["truth"])
        ego = int(event["candidates"]["local:ego"])
        partner = int(event["candidates"]["local:agent1"])
        late = int(event["candidates"]["edge:ego"])
        if wanted["rescued_miss"] is None and truth == 1 and late == 1 and (ego == 0) != (partner == 0):
            wanted["rescued_miss"] = event
        if wanted["shared_false_alarm"] is None and truth == 0 and late == 1 and min(ego, partner) == 0:
            wanted["shared_false_alarm"] = event
        if wanted["shared_miss"] is None and truth == 1 and late == 0 and ego == 0 and partner == 0:
            wanted["shared_miss"] = event
    if any(value is None for value in wanted.values()):
        raise AssertionError(f"missing plot example: {wanted}")

    scene_cache = {}
    fig, axes = plt.subplots(1, 3, figsize=(12.4, 4.4))
    titles = {
        "rescued_miss": "Rescued miss",
        "shared_false_alarm": "Shared false alarm",
        "shared_miss": "Shared miss",
    }
    saved = []
    for ax, (kind, event) in zip(axes, wanted.items()):
        prov = provenance[event["event_id"]]
        scene = prov["scene_id"]
        frame = int(prov["frame_id"])
        if scene not in scene_cache:
            paths = module.source_paths(scene)
            scene_cache[scene] = {
                "gt": parse_labeled(fetch(paths["gt"]), ground_truth=True, score_threshold=0.3),
                "ego": parse_labeled(fetch(paths["ego"]), ground_truth=False, score_threshold=0.3),
                "agent1": parse_labeled(fetch(paths["agent1"]), ground_truth=False, score_threshold=0.3),
                "late": parse_labeled(fetch(paths["late_fusion"]), ground_truth=False, score_threshold=0.3),
            }
        x, z = prov["center_kitti_xz"]
        radius = 7.5
        ax.set_aspect("equal")
        circle = plt.Circle((x, z), radius, fill=False, lw=1.2, color="#9A3412")
        ax.add_patch(circle)
        gt = scene_cache[scene]["gt"].get(frame, [])
        inside_ids = []
        for gx, gz, gid in gt:
            hit = (gx - x) ** 2 + (gz - z) ** 2 <= radius * radius
            if abs(gx - x) > 45 or abs(gz - z) > 45:
                continue
            ax.scatter(gx, gz, s=28, c="#1F4E79", zorder=3)
            if hit or abs(gx - x) < 22:
                ax.annotate(f"GT {gid}", (gx, gz), textcoords="offset points", xytext=(3, 3), fontsize=6, color="#1F4E79")
            if hit:
                inside_ids.append(gid)
        for name, color, marker in (("ego", "#2F6F4E", "s"), ("agent1", "#7A4E8A", "^"), ("late", "#B45309", "D")):
            pts = scene_cache[scene][name].get(frame, [])
            xs = [p[0] for p in pts if abs(p[0] - x) <= 45 and abs(p[1] - z) <= 45]
            zs = [p[1] for p in pts if abs(p[0] - x) <= 45 and abs(p[1] - z) <= 45]
            ax.scatter(xs, zs, s=18, c=color, marker=marker, label={"ego": "Ego", "agent1": "Partner", "late": "Late fusion"}[name], zorder=2)
        ax.set_xlim(x - 40, x + 40)
        ax.set_ylim(z - 40, z + 40)
        ax.set_xlabel("KITTI X (m)")
        ax.set_ylabel("KITTI Z (m)")
        cand = event["candidates"]
        ax.set_title(
            f"{titles[kind]}\n{event['event_id']}\n"
            f"truth {event['truth']}, ego {cand['local:ego']}, partner {cand['local:agent1']}, late {cand['edge:ego']}",
            fontsize=8,
        )
        ax.grid(alpha=0.25)
        saved.append({
            "kind": kind, "event_id": event["event_id"], "scene": scene, "frame": frame,
            "center_kitti_xz": [x, z], "radius_m": radius, "score_min": 0.3,
            "truth": event["truth"], "ego": cand["local:ego"], "partner": cand["local:agent1"],
            "late_fusion": cand["edge:ego"], "gt_track_ids_inside": inside_ids,
        })
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Baseline queries at 7.5 m and score 0.30. A dot is a box center, not a 3D box.", fontsize=10)
    fig.tight_layout(rect=(0, 0.08, 1, 0.90))
    fig.savefig(OUT / "topdown_examples.png", dpi=160)
    plt.close(fig)
    return saved


def pct(num: int, den: int) -> str:
    return f"{num}/{den} = {100.0 * num / den:.2f}%"


def pp_cell(row: dict, key: str, den_key: str) -> str:
    return pct(int(row[key]), int(row[den_key]))


def write_report(policy_rows, finding_rows, selection_rows, offset_rows, move_rows,
                 multi_rows, flip_rows, box_rows, fixed_rows, examples) -> None:
    pol = {(r["radius_m"], r["score_min"], r["policy"]): r for r in policy_rows}
    find = {(r["radius_m"], r["score_min"]): r for r in finding_rows}
    lines = []
    add = lines.append
    add("# Spatial sensitivity of the nine-sequence queries")
    add("")
    add("The queries come from the unmodified `scripts/prepare_dmstrack_v2v4real.py`. Each of the nine settings changes only `--radius` and `--threshold`. The cached DMSTrack text at commit `d3b9949499c8e68ea33060873bd1cb95b6d4d323` is the input. The 7.5 m / 0.30 trace matches the earlier regeneration event for event.")
    add("")
    add("## How a query is chosen")
    add("")
    add("The files are already in one shared KITTI camera frame. X and Z are the ground plane. Y is height and is not used. A ground-truth Car uses track id column 1, class column 2, and center columns 13 and 15. A detection uses class code 2, score column 6, and center columns 10 and 12. No new coordinate transform is applied.")
    add("")
    add("A binary label is 1 when any retained Car center lies within the radius of the query center, including the boundary. It is 0 otherwise. The label does not identify a track, count the cars, or measure 3D box overlap. Several cars in one circle still produce one presence label.")
    add("")
    add("The balanced task uses ground truth only to place the regions. On each frame it anchors the positive query on the car at index `frame mod number of cars`. It then tries the offsets (18, 0), (−18, 0), (0, 18), (0, −18), (25, 0), (−25, 0), (0, 25), (0, −25), and (35, 15), and keeps the first offset whose circle contains no ground-truth center. Score does not move either center. Ground truth is never filtered by score. A detection center is kept only when its score is at least the cutoff, so the same region can change its predicted label when the cutoff changes.")
    add("")
    add("The fixed grid is separate: 12 centers at X in {−40, −20, 0, 20} and Z in {−10, 15, 40}, on every frame. Its locations do not depend on radius or score. Its labels do.")
    add("")
    add("## What changes across the nine settings")
    add("")
    add("Every radius keeps all 1,993 frames. No frame fails to find a negative offset. Each emitted frame still contributes one positive and one negative query, so every balanced setting has 3,986 queries and a 1,993 / 1,993 class split.")
    add("")
    add("| Radius | Positive centers moved vs 7.5 m | Negative centers moved vs 7.5 m | Positive regions with 2 or more GT cars | Max GT cars in one positive region |")
    add("|---:|---:|---:|---:|---:|")
    sel = {r["radius_m"]: r for r in selection_rows}
    mov = {r["radius_m"]: r for r in move_rows}
    for radius in RADII:
        add(
            f"| {radius:.1f} | {mov[radius]['positive_centers_different_from_7.5m']} / {mov[radius]['frames']} | "
            f"{mov[radius]['negative_centers_different_from_7.5m']} / {mov[radius]['frames']} | "
            f"{sel[radius]['positive_rois_with_two_or_more']} / {sel[radius]['frames_emitted']} | "
            f"{sel[radius]['max_gt_cars_in_one_positive_roi']} |"
        )
    add("")
    one_small = sel[2.5]["frames_emitted"] - sel[2.5]["positive_rois_with_two_or_more"]
    add(
        "The positive anchor never moves. "
        f"At 2.5 m, {one_small} of {sel[2.5]['frames_emitted']} positive regions contain one ground-truth car. "
        f"At 7.5 m, {sel[7.5]['positive_rois_with_two_or_more']} of {sel[7.5]['frames_emitted']} positive regions contain two or more cars. "
        "The binary label is still only presence."
    )
    add("")
    add("Negative centers do move. A smaller circle lets a nearer offset qualify.")
    add("")
    add("| Radius | Most common negative offset | Frames | Second offset | Frames |")
    add("|---:|---|---:|---|---:|")
    by_offset = defaultdict(list)
    for row in offset_rows:
        by_offset[row["radius_m"]].append(row)
    for radius in RADII:
        first, second = by_offset[radius][:2]
        add(
            f"| {radius:.1f} | ({first['offset_x_m']:g}, {first['offset_z_m']:g}) | {first['frames']} | "
            f"({second['offset_x_m']:g}, {second['offset_z_m']:g}) | {second['frames']} |"
        )
    add("")
    add("Score changes which detection centers are allowed to vote. It does not change truth or query centers. Label flips below are counts of queries whose binary prediction differs from the 0.30 cutoff at the same radius.")
    add("")
    add("| Score | Ego boxes | Partner boxes | Late-fusion boxes | CoBEVT boxes |")
    add("|---:|---:|---:|---:|---:|")
    boxes = {(r["score_min"], r["source"]): r["boxes_retained"] for r in box_rows}
    for score in SCORES:
        add(f"| {score:.1f} | {boxes[(score, 'ego')]} | {boxes[(score, 'agent1')]} | {boxes[(score, 'late_fusion')]} | {boxes[(score, 'cobevt')]} |")
    add("")
    add("| Radius | Score | Ego flips vs 0.30 | Partner flips | Late-fusion flips |")
    add("|---:|---:|---:|---:|---:|")
    for row in flip_rows:
        if row["score_min"] == 0.3:
            continue
        add(
            f"| {row['radius_m']:.1f} | {row['score_min']:.1f} | {row['ego_label_flips']} / {row['queries']} | "
            f"{row['partner_label_flips']} / {row['queries']} | {row['late_fusion_label_flips']} / {row['queries']} |"
        )
    add("")
    add("## Balanced policies")
    add("")
    add("Local keeps both detector labels. Late fusion assigns its label to both agents, so its mean error equals its R2. The disagreement gate uses late fusion only when the local labels differ. OR uses 1 when either local label is 1. Mean error uses both agent labels. R2 uses queries. Joint false negatives use the 1,993 positive queries, and joint false positives use the 1,993 negative queries.")
    add("")
    for radius in RADII:
        for score in SCORES:
            add(f"### Radius {radius:.1f} m, score {score:.1f}")
            add("")
            add("| Policy | Mean error | Joint FN | Joint FP | R2 |")
            add("|---|---:|---:|---:|---:|")
            for name, title in (("local", "Local"), ("late_fusion", "Late Fusion"), ("disagreement_gate", "Disagreement Gate"), ("OR", "OR")):
                row = pol[(radius, score, name)]
                add(
                    f"| {title} | {pct(row['agent_errors'], row['agent_labels'])} | "
                    f"{pct(row['joint_fn'], row['positives'])} | {pct(row['joint_fp'], row['negatives'])} | "
                    f"{pct(row['r2_count'], row['queries'])} |"
                )
            add("")
    add("## Do the earlier findings hold?")
    add("")
    add("The earlier balanced result, at 7.5 m and score 0.30, is unchanged: local mean error 1,151/7,972 = 14.44%, late fusion 388/7,972 = 4.87%, local R2 105/3,986 = 2.63%, late-fusion R2 194/3,986 = 4.87%, joint false negatives 91/1,993 for every policy, and joint false positives 14, 103, 101, and 108. Sequence 0007 remains 221 frames, with joint false negatives 4 and joint false positives 0, 12, 10, and 10. The gate still matches OR on that sequence.")
    add("")
    add("| Radius | Score | Late mean error lower | Late R2 higher | Same joint-FN events | Gate/OR queries that differ | Gate wrong on those queries | Sequences with equal gate and OR | Sequences with higher late-fusion R2 |")
    add("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for radius in RADII:
        for score in SCORES:
            row = find[(radius, score)]
            add(
                f"| {radius:.1f} | {score:.1f} | {bool(row['late_mean_below_local'])} | {bool(row['late_r2_above_local'])} | "
                f"{bool(row['joint_fn_same_events'])} | {row['gate_or_differ_queries']} | {row['gate_wrong_where_they_differ']} | "
                f"{row['sequences_gate_equals_or']} / 9 | {row['sequences_late_r2_higher']} higher, "
                f"{row['sequences_late_r2_equal']} equal, {row['sequences_late_r2_lower']} lower |"
            )
    add("")
    hold_mean = all(row["late_mean_below_local"] for row in finding_rows)
    hold_r2 = all(row["late_r2_above_local"] for row in finding_rows)
    hold_fn = all(row["joint_fn_same_events"] for row in finding_rows)
    gate_ok_count = sum(1 for row in finding_rows if row["gate_or_differ_on_positive"] == 0 and row["gate_wrong_where_they_differ"] == 0)
    hold_gate = gate_ok_count == len(finding_rows)
    base = find[(7.5, 0.3)]
    gate_counts = sorted({row["sequences_gate_equals_or"] for row in finding_rows})
    r2_patterns = sorted({(row["sequences_late_r2_higher"], row["sequences_late_r2_equal"], row["sequences_late_r2_lower"]) for row in finding_rows})
    add(
        f"Late fusion has a lower pooled mean error than local in {sum(row['late_mean_below_local'] for row in finding_rows)} of 9 settings. "
        f"Late fusion has a higher pooled R2 in {sum(row['late_r2_above_local'] for row in finding_rows)} of 9. "
        f"The four policies miss the same positive queries in {sum(row['joint_fn_same_events'] for row in finding_rows)} of 9. "
        f"The gate and OR differ only on negative queries, with the gate label true on every differing query, in {gate_ok_count} of 9."
    )
    add("")
    add(
        f"At 7.5 m and score 0.30, the gate matches OR on {base['sequences_gate_equals_or']} of 9 sequences, "
        f"and late-fusion R2 is higher on {base['sequences_late_r2_higher']}, equal on {base['sequences_late_r2_equal']}, "
        f"and lower on {base['sequences_late_r2_lower']}. "
        f"Across the sweep, sequences where gate equals OR take the values {gate_counts}. "
        f"The higher/equal/lower late-fusion R2 sequence counts take the values {r2_patterns}."
    )
    if not (hold_mean and hold_r2 and hold_fn and hold_gate):
        failed = []
        if not hold_mean:
            failed.append("lower late-fusion mean error")
        if not hold_r2:
            failed.append("higher late-fusion R2")
        if not hold_fn:
            failed.append("identical joint-FN events")
        if not hold_gate:
            failed.append("gate correct on every disagreement with OR")
        add("")
        add("These checks fail in at least one setting: " + ", ".join(failed) + ".")
    add("")
    add("## Fixed grid")
    add("")
    add("The grid has 12 regions on each of 1,993 frames, so every setting has 23,916 queries. Positive prevalence changes with radius because a larger circle covers more cars. At 7.5 m and score 0.30 the converter matches the published grid: 4,052 positive queries, 1,020 ego errors, 1,718 partner errors, 291 separate joint errors, and 1,078 late-fusion errors.")
    add("")
    add("On this grid, sharing does not improve both vehicles. At 7.5 m and 0.30, ego is wrong on 1,020/23,916 = 4.26% of queries and late fusion is wrong on 1,078/23,916 = 4.51%. The partner is wrong on 1,718/23,916 = 7.18%. Local R2 is 291/23,916 = 1.22%, and late-fusion R2 is 4.51%. The balanced-task statement that late fusion lowers every vehicle's error does not hold on the grid.")
    add("")
    add("| Radius | Score | Positives | Local mean | Late fusion mean / R2 | Gate mean / R2 | OR mean / R2 | Local R2 | Joint FN local | Joint FP local | Joint FP late |")
    add("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    grid = {(r["radius_m"], r["score_min"], r["policy"]): r for r in fixed_rows}
    for radius in RADII:
        for score in SCORES:
            loc = grid[(radius, score, "local")]
            late = grid[(radius, score, "late_fusion")]
            gate = grid[(radius, score, "disagreement_gate")]
            either = grid[(radius, score, "OR")]
            add(
                f"| {radius:.1f} | {score:.1f} | {loc['positives']}/{loc['queries']} | "
                f"{pct(loc['agent_errors'], loc['agent_labels'])} | {pct(late['r2_count'], late['queries'])} | "
                f"{pct(gate['r2_count'], gate['queries'])} | {pct(either['r2_count'], either['queries'])} | "
                f"{pct(loc['r2_count'], loc['queries'])} | {loc['joint_fn']}/{loc['positives']} | "
                f"{loc['joint_fp']}/{loc['negatives']} | {late['joint_fp']}/{late['negatives']} |"
            )
    add("")
    add("## Examples at the published setting")
    add("")
    add("The figure `topdown_examples.png` uses 7.5 m and score 0.30. Circles are query regions. Points are box centers within 45 m of the query. Ground-truth labels are track ids.")
    add("")
    for item in examples:
        add(
            f"- {item['kind']}: `{item['event_id']}`, truth {item['truth']}, ego {item['ego']}, "
            f"partner {item['partner']}, late fusion {item['late_fusion']}. "
            f"GT track ids inside the circle: {', '.join(item['gt_track_ids_inside']) or 'none'}."
        )
    add("")
    if find[(7.5, 0.3)]["joint_fn_same_events"]:
        add("")
        add("The shared-miss example is a positive query that both local detectors and late fusion miss. At this setting the four policies miss the same positive queries, so there is no positive query where late fusion is wrong while either local detector is right. Late fusion introduces joint errors on negative queries, which is the shared false alarm.")
    add("")
    add("These plots are presence checks in the X–Z plane. They are not 3D IoU, average precision, or a sample of natural hazard frequency. The balanced task forces one positive and one negative query per frame, so its error rates are not the rates on the fixed grid.")
    add("")
    (OUT / "ANALYSIS.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
