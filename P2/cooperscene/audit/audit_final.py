"""Final audit of the frozen CooperScene three-vehicle export.

Recomputes every policy from the exported rows, checks the paired label
transitions, and draws the world-coordinate regions where a correct local
detection is overwritten. The frozen score, radius, and grid are not changed.
Octopus-main is imported and not edited. Detector inference is not run.
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
from matplotlib.patches import Circle
import numpy as np

ROOT = Path(__file__).resolve().parents[4] / "Octopus-main"
sys.path.insert(0, str(ROOT))
EVAL = Path(__file__).resolve().parents[1] / "evaluation"
sys.path.insert(0, str(EVAL))

from run_evaluation import (  # noqa: E402
    AGENTS, BOOTSTRAP_DRAWS, BOOTSTRAP_SEED, EXPORT, PREPARED,
    decide_all, event_counts, expert_from_validation, fusers_for,
    observation, reliability, study_config, summarize,
)

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
ORIGIN = (-75.0, -105.0)
SPACING = 15.0
RADIUS = 7.5
METHODS = ("local", "majority", "weighted", "conservative_f0", "expert_override", "always_a")
BLOCK_LENGTHS = (1, 2, 5, 10)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def key_of(row: dict) -> tuple:
    take = row.get("take_id", "1")
    frame = row.get("frame_token", row.get("frame_id", "").rsplit(":", 1)[-1])
    roi = row.get("roi_id", row.get("event_id", "").rsplit(":", 1)[-1])
    return str(take), str(frame), str(roi)


def on_lattice(point) -> bool:
    ix = (float(point[0]) - ORIGIN[0]) / SPACING
    iy = (float(point[1]) - ORIGIN[1]) / SPACING
    return abs(ix - round(ix)) < 1e-6 and abs(iy - round(iy)) < 1e-6


def audit_files() -> dict:
    predictions = load_jsonl(EXPORT / "predictions.jsonl")
    truth_rows = load_jsonl(EXPORT / "ground_truth.jsonl")
    per = {agent: load_jsonl(EXPORT / f"vehicle_{agent}_predictions.jsonl") for agent in AGENTS}
    trace = load_jsonl(PREPARED / "trace.jsonl")
    manifest = json.loads((EXPORT / "manifest.json").read_text(encoding="utf-8"))
    protocol = json.loads((EXPORT / "protocol_check.json").read_text(encoding="utf-8"))
    problems = []
    if not (len(predictions) == len(truth_rows) == len(trace) == 1200):
        problems.append("row_count")
    if any(len(per[agent]) != len(predictions) for agent in AGENTS):
        problems.append("per_vehicle_count")
    centers = {}
    frames = defaultdict(list)
    positive = 0
    radii = set()
    for index, row in enumerate(predictions):
        identity = key_of(row)
        if key_of(truth_rows[index]) != identity or key_of(trace[index]) != identity:
            problems.append(f"alignment_{index}")
            break
        if int(truth_rows[index]["truth"]) != int(row["truth"]) or int(trace[index]["truth"]) != int(row["truth"]):
            problems.append(f"truth_{index}")
            break
        votes = {}
        for agent in AGENTS:
            vehicle = per[agent][index]
            if key_of(vehicle) != identity or str(vehicle["vehicle_id"]) != agent:
                problems.append(f"vehicle_key_{agent}_{index}")
                break
            if int(vehicle["prediction"]) != int(row["predictions"][agent]):
                problems.append(f"vehicle_bit_{agent}_{index}")
                break
            if int(trace[index]["candidates"][f"local:{agent}"]) != int(row["predictions"][agent]):
                problems.append(f"trace_bit_{agent}_{index}")
                break
            votes[agent] = int(row["predictions"][agent])
        center = tuple(row["roi"]["center_xy_m"])
        radius = float(row["roi"]["radius_m"])
        radii.add(radius)
        if row["roi"]["frame"] != "cooperscene_global_xy_m" or not on_lattice(center):
            problems.append(f"geometry_{index}")
            break
        if identity[2] in centers and centers[identity[2]] != center:
            problems.append(f"roi_center_changed_{identity[2]}")
            break
        centers[identity[2]] = center
        if len({int(bit) for bit in list(votes.values()) + [int(row["truth"])]} - {0, 1}) :
            problems.append(f"nonbinary_{index}")
            break
        positive += int(row["truth"])
        frames[identity[1]].append(row)
    runs = manifest["physical_detector_runs"]
    if len(set(runs.values())) != 3:
        problems.append("run_ids")
    if len(set(manifest["checkpoint_sha256"].values())) != 1:
        problems.append("checkpoint")
    counts = [len(items) for items in frames.values()]
    tokens = sorted(int(token) for token in frames)
    if tokens != list(range(tokens[0], tokens[0] + len(tokens))):
        problems.append("frame_gap")
    if problems:
        raise SystemExit("AUDIT_FILE_REJECTED " + ",".join(problems[:8]))
    return {
        "rows": len(predictions),
        "frames": len(frames),
        "frame_tokens": [str(token) for token in tokens],
        "rois_per_frame": {
            "min": int(min(counts)),
            "median": float(np.median(counts)),
            "max": int(max(counts)),
        },
        "distinct_centers": len(centers),
        "radius_m": sorted(radii),
        "lattice_origin_m": list(ORIGIN),
        "lattice_spacing_m": SPACING,
        "positive_truth_regions": positive,
        "run_ids": runs,
        "checkpoint_sha256": next(iter(manifest["checkpoint_sha256"].values())),
        "validation_gate_passed": bool(protocol["passed"]),
        "validation_gate_failures": protocol["gate_failures"],
        "ego_gt": protocol["ego_gt"],
        "ego_predictions": protocol["ego_predictions_at_or_above_score"],
        "validation_label_disagreements": protocol["label_disagreements"],
        "validation_common_decisions": protocol["common_decisions"],
        "validation_disagreement_rate": protocol["label_disagreement_rate"],
        "predictions": predictions,
        "frames": frames,
        "manifest": manifest,
    }


def policy_arrays(checked: dict):
    manifest = checked["manifest"]
    scenario = json.loads((PREPARED / "scenario.json").read_text(encoding="utf-8"))
    config = study_config(scenario)
    expert = expert_from_validation(manifest["assumed_source_error"])
    built = fusers_for(config, expert)
    rates = manifest["assumed_source_error"]
    order = checked["frame_tokens"]
    geometry = []
    packs = {method: [] for method in METHODS}
    reasons = []
    for token in order:
        rows = []
        for row in checked["frames"][token]:
            rows.append({
                "event_id": f"CooperScene:test:1:{token}:{row['roi_id']}",
                "frame_id": f"CooperScene:test:1:{token}",
                "truth": int(row["truth"]),
                "candidates": {f"local:{agent}": int(row["predictions"][agent]) for agent in AGENTS},
                "center": tuple(row["roi"]["center_xy_m"]),
                "roi_id": row["roi_id"],
                "frame_token": token,
            })
        frame_rows = [
            {"event_id": row["event_id"], "frame_id": row["frame_id"], "truth": row["truth"], "candidates": row["candidates"]}
            for row in rows
        ]
        truth, local, _final, _accepted = decide_all(frame_rows, "local", built, rates, expert, False)
        packs["local"].append((truth, local, local, np.zeros(len(frame_rows), dtype=bool)))
        for method in METHODS:
            if method == "local":
                continue
            truth, local, final, accepted = decide_all(frame_rows, method, built, rates, expert, False)
            packs[method].append((truth, local, final, accepted))
        q = reliability(rates)
        for row in rows:
            decision = built["conservative_f0"].decide(observation(row, False), q)
            reasons.append({
                "frame_token": token,
                "roi_id": row["roi_id"],
                "center": row["center"],
                "truth": row["truth"],
                "local": [int(row["candidates"][f"local:{agent}"]) for agent in AGENTS],
                "accepted": bool(decision.shared),
                "reasons": list(decision.fallback_reasons),
                "confidence": float(decision.score_confidence),
            })
        geometry.append(rows)
    return packs, reasons, geometry, expert


def transition_table(truth, local, final) -> dict:
    local_wrong = (local != truth[:, None]).sum(axis=1)
    final_wrong = (final != truth[:, None]).sum(axis=1)
    table = Counter(zip(local_wrong.tolist(), final_wrong.tolist()))
    lost = (truth[:, None] == 1) & (local == 1) & (final == 0)
    gained_alarm = (truth[:, None] == 0) & (local == 0) & (final == 1)
    by_vehicle = {}
    for index, agent in enumerate(AGENTS):
        by_vehicle[agent] = {
            "corrections": int(((local[:, index] != truth) & (final[:, index] == truth)).sum()),
            "introduced": int(((local[:, index] == truth) & (final[:, index] != truth)).sum()),
            "lost_correct_detections": int(lost[:, index].sum()),
            "introduced_false_alarms": int(gained_alarm[:, index].sum()),
        }
    return {
        "wrong_count": {f"{left}_to_{right}": int(count) for (left, right), count in sorted(table.items())},
        "lost_correct_detections": int(lost.sum()),
        "introduced_false_alarms": int(gained_alarm.sum()),
        "by_vehicle": by_vehicle,
    }


def pattern_name(bits) -> str:
    wrong = [agent for agent, bit in zip(AGENTS, bits) if int(bit) == 1]
    return "none" if not wrong else "+".join(wrong)


def classify_patterns(packs, reasons) -> dict:
    truth = np.concatenate([item[0] for item in packs["local"]])
    local = np.concatenate([item[1] for item in packs["local"]])
    final_f0 = np.concatenate([item[2] for item in packs["conservative_f0"]])
    accepted = np.array([row["accepted"] for row in reasons])
    local_wrong = local != truth[:, None]
    count = local_wrong.sum(axis=1)
    out = {"single": {}, "double": {}}
    for name, mask in (("single", count == 1), ("double", count == 2)):
        groups = Counter()
        accepted_groups = Counter()
        for index in np.flatnonzero(mask):
            who = pattern_name(local_wrong[index])
            groups[who] += 1
            if accepted[index]:
                accepted_groups[who] += 1
        out[name] = {
            who: {"regions": int(groups[who]), "f0_accepted": int(accepted_groups[who])}
            for who in sorted(groups)
        }
    changed = final_f0 != local
    if int(changed[accepted == 0].sum()) != 0:
        raise SystemExit("AUDIT_F0_CHANGED_A_REJECTED_REGION")
    return out


def lost_cases(packs, geometry) -> list[dict]:
    cases = []
    offset = 0
    flat = [row for frame in geometry for row in frame]
    truth = np.concatenate([item[0] for item in packs["local"]])
    local = np.concatenate([item[1] for item in packs["local"]])
    majority = np.concatenate([item[2] for item in packs["majority"]])
    f0 = np.concatenate([item[2] for item in packs["conservative_f0"]])
    for index, row in enumerate(flat):
        if int(truth[index]) != 1:
            continue
        for agent_index, agent in enumerate(AGENTS):
            if int(local[index, agent_index]) != 1:
                continue
            lost_majority = int(majority[index, agent_index]) == 0
            lost_f0 = int(f0[index, agent_index]) == 0
            if lost_majority or lost_f0:
                cases.append({
                    "frame_token": row["frame_token"],
                    "roi_id": row["roi_id"],
                    "center_xy_m": [float(row["center"][0]), float(row["center"][1])],
                    "vehicle": agent,
                    "local": [int(bit) for bit in local[index]],
                    "majority": [int(bit) for bit in majority[index]],
                    "conservative_f0": [int(bit) for bit in f0[index]],
                    "lost_by_majority": lost_majority,
                    "lost_by_f0": lost_f0,
                })
        offset += 0
    return cases


def neighbor_pairs(frames: dict) -> list[tuple]:
    pairs = []
    for token, rows in frames.items():
        points = [(row["roi_id"], np.array(row["roi"]["center_xy_m"], dtype=float),
                   [int(row["predictions"][agent]) for agent in AGENTS], int(row["truth"])) for row in rows]
        for left in range(len(points)):
            for right in range(left + 1, len(points)):
                delta = np.abs(points[left][1] - points[right][1])
                orthogonal = (
                    (abs(delta[0] - SPACING) < 1e-6 and delta[1] < 1e-6)
                    or (abs(delta[1] - SPACING) < 1e-6 and delta[0] < 1e-6)
                )
                if orthogonal:
                    pairs.append((token, points[left], points[right]))
    return pairs


def dependence(frames: dict) -> dict:
    pairs = neighbor_pairs(frames)
    per_vehicle = {}
    both_double = 0
    one_double = 0
    double_regions = 0
    double_ids = set()
    neighbors = defaultdict(set)
    for token, rows in frames.items():
        for row in rows:
            votes = [int(row["predictions"][agent]) for agent in AGENTS]
            wrong = sum(bit != int(row["truth"]) for bit in votes)
            if wrong >= 2:
                double_regions += 1
                double_ids.add((token, row["roi_id"]))
    for token, left, right in pairs:
        neighbors[(token, left[0])].add(right[0])
        neighbors[(token, right[0])].add(left[0])
        left_double = (token, left[0]) in double_ids
        right_double = (token, right[0]) in double_ids
        if left_double or right_double:
            one_double += 1
        if left_double and right_double:
            both_double += 1
    double_with_double_neighbor = sum(
        1 for token, roi in double_ids
        if any((token, other) in double_ids for other in neighbors[(token, roi)])
    )
    for index, agent in enumerate(AGENTS):
        left_err = []
        right_err = []
        for _token, left, right in pairs:
            left_err.append(int(left[2][index] != left[3]))
            right_err.append(int(right[2][index] != right[3]))
        left_arr = np.array(left_err)
        right_arr = np.array(right_err)
        correlation = None if left_arr.std() == 0 or right_arr.std() == 0 else float(np.corrcoef(left_arr, right_arr)[0, 1])
        per_vehicle[agent] = {
            "neighbor_pairs": int(len(pairs)),
            "correlation": correlation,
            "error_rate": float(left_arr.mean()),
            "both_wrong": int(((left_arr == 1) & (right_arr == 1)).sum()),
            "expected_both_if_independent": float(left_arr.mean() * right_arr.mean() * len(pairs)),
        }
    temporal = temporal_dependence(frames)
    return {
        "orthogonal_neighbor_pairs": int(len(pairs)),
        "per_vehicle": per_vehicle,
        "double_error_regions": int(double_regions),
        "double_error_regions_with_a_double_error_neighbor": int(double_with_double_neighbor),
        "neighbor_pairs_touching_a_double_error": int(one_double),
        "neighbor_pairs_with_two_double_errors": int(both_double),
        "temporal_lag1": temporal,
    }


def temporal_dependence(frames: dict) -> dict:
    tokens = sorted(frames, key=int)
    by_token = {}
    for token, rows in frames.items():
        by_token[token] = {row["roi_id"]: row for row in rows}
    per_vehicle = {agent: {"pairs": 0, "left": [], "right": []} for agent in AGENTS}
    same_region_pairs = 0
    for earlier, later in zip(tokens, tokens[1:]):
        if int(later) - int(earlier) != 1:
            continue
        shared = set(by_token[earlier]) & set(by_token[later])
        same_region_pairs += len(shared)
        for roi in shared:
            left = by_token[earlier][roi]
            right = by_token[later][roi]
            for agent in AGENTS:
                per_vehicle[agent]["left"].append(int(int(left["predictions"][agent]) != int(left["truth"])))
                per_vehicle[agent]["right"].append(int(int(right["predictions"][agent]) != int(right["truth"])))
    out = {"consecutive_frame_steps": len(tokens) - 1, "same_region_pairs": same_region_pairs}
    for agent in AGENTS:
        left = np.array(per_vehicle[agent]["left"])
        right = np.array(per_vehicle[agent]["right"])
        correlation = None if len(left) == 0 or left.std() == 0 or right.std() == 0 else float(np.corrcoef(left, right)[0, 1])
        out[agent] = {
            "pairs": int(len(left)),
            "correlation": correlation,
            "both_wrong": int(((left == 1) & (right == 1)).sum()) if len(left) else 0,
        }
    return out


def block_bootstrap(packs, length: int, seed: int, draws: int) -> dict:
    n = len(packs["local"])
    starts_hi = n - length + 1
    n_blocks = n // length
    out = {}
    for method in METHODS:
        if method == "local":
            continue
        rng = np.random.default_rng(seed)
        deltas = {key: [] for key in ("mean_error", "r2", "r3")}
        for _ in range(draws):
            if length == 1:
                pick = rng.integers(0, n, n)
            else:
                starts = rng.integers(0, starts_hi, n_blocks)
                pick = [start + offset for start in starts for offset in range(length)]
            chosen = [packs[method][index] for index in pick]
            policy = summarize(chosen, method)
            local = event_counts(
                np.concatenate([item[0] for item in chosen]),
                np.concatenate([item[1] for item in chosen]),
            )
            for key in deltas:
                deltas[key].append(policy[key] - local[key])
        out[method] = {}
        for key, values in deltas.items():
            array = np.asarray(values)
            out[method][key] = [float(np.quantile(array, 0.025)), float(np.quantile(array, 0.975))]
    out["draws"] = draws
    out["seed"] = seed
    out["block_length_frames"] = length
    out["blocks_per_draw"] = n if length == 1 else n_blocks
    return out


def draw_case(case, frame_rows, path: Path, title: str):
    centers = np.array([row["roi"]["center_xy_m"] for row in frame_rows], dtype=float)
    focus = np.array(case["center_xy_m"], dtype=float)
    figure, axes = plt.subplots(1, 2, figsize=(11.2, 5.4))
    for axis, zoom in zip(axes, (False, True)):
        axis.set_aspect("equal")
        for row in frame_rows:
            center = np.array(row["roi"]["center_xy_m"], dtype=float)
            votes = [int(row["predictions"][agent]) for agent in AGENTS]
            truth = int(row["truth"])
            is_focus = row["roi_id"] == case["roi_id"]
            if is_focus:
                face, edge, width = "#e85d4c", "#7a1f16", 1.8
            elif truth == 1:
                face, edge, width = "#d6e6f5", "#2f5573", 0.8
            elif any(bit != truth for bit in votes):
                face, edge, width = "#f6e2ad", "#8a6a22", 0.8
            else:
                face, edge, width = "#f3f3f3", "#b5b5b5", 0.6
            axis.add_patch(Circle(center, RADIUS, facecolor=face, edgecolor=edge, linewidth=width, alpha=0.95))
            if zoom and (is_focus or np.linalg.norm(center - focus) <= 30.1):
                label = " ".join(str(bit) for bit in votes)
                axis.text(center[0], center[1], label, ha="center", va="center", fontsize=8, color="#1c1c1c")
        axis.plot(focus[0], focus[1] + RADIUS + 1.6, marker="x", color="#7a1f16", markersize=8, markeredgewidth=1.5)
        if zoom:
            axis.set_xlim(focus[0] - 42, focus[0] + 42)
            axis.set_ylim(focus[1] - 42, focus[1] + 42)
            axis.set_title("Neighbors within 30 m. Text is vehicles 1 2 3.")
        else:
            pad = 12
            axis.set_xlim(centers[:, 0].min() - RADIUS - pad, centers[:, 0].max() + RADIUS + pad)
            axis.set_ylim(centers[:, 1].min() - RADIUS - pad, centers[:, 1].max() + RADIUS + pad)
            axis.set_title("Every common region in the frame")
        axis.set_xlabel("World x (m)")
        axis.set_ylabel("World y (m)")
        axis.grid(True, linewidth=0.3, alpha=0.4)
    figure.suptitle(title, fontsize=11)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def draw_map(cases, frames, path: Path):
    figure, axis = plt.subplots(figsize=(7.4, 6.2))
    axis.set_aspect("equal")
    seen = set()
    for rows in frames.values():
        for row in rows:
            center = tuple(row["roi"]["center_xy_m"])
            if center in seen:
                continue
            seen.add(center)
            axis.add_patch(Circle(center, RADIUS, facecolor="#f7f7f7", edgecolor="#d0d0d0", linewidth=0.5))
    both_counts = Counter(tuple(case["center_xy_m"]) for case in cases if case["lost_by_f0"])
    only_counts = Counter(tuple(case["center_xy_m"]) for case in cases if case["lost_by_majority"] and not case["lost_by_f0"])
    if both_counts:
        both = np.array(list(both_counts), dtype=float)
        axis.scatter(both[:, 0], both[:, 1], s=36, c="#e85d4c", label=f"Lost by majority and F0 ({sum(both_counts.values())})", zorder=3)
        for center, count in both_counts.items():
            axis.annotate(str(count), center, textcoords="offset points", xytext=(7, 6), color="#7a1f16", fontsize=8)
    if only_counts:
        only = np.array(list(only_counts), dtype=float)
        axis.scatter(only[:, 0], only[:, 1], s=42, facecolors="none", edgecolors="#1f4e79", linewidths=1.4,
                     label=f"Lost by majority, kept by F0 ({sum(only_counts.values())})", zorder=4)
        for center, count in only_counts.items():
            axis.annotate(str(count), center, textcoords="offset points", xytext=(7, -10), color="#1f4e79", fontsize=8)
    points = np.array(list(seen), dtype=float)
    pad = 14
    axis.set_xlim(points[:, 0].min() - RADIUS - pad, points[:, 0].max() + RADIUS + pad)
    axis.set_ylim(points[:, 1].min() - RADIUS - pad, points[:, 1].max() + RADIUS + pad)
    axis.set_xlabel("World x (m)")
    axis.set_ylabel("World y (m)")
    axis.set_title("Correct local detections overwritten on the test grid")
    axis.legend(loc="best", frameon=False)
    axis.grid(True, linewidth=0.3, alpha=0.4)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def choose_case(cases, frames, f0_also: bool) -> dict:
    eligible = [case for case in cases if case["lost_by_f0"] is f0_also and case["lost_by_majority"]]
    ranked = []
    for case in eligible:
        rows = frames[case["frame_token"]]
        focus = np.array(case["center_xy_m"], dtype=float)
        neighbors = 0
        for row in rows:
            if row["roi_id"] == case["roi_id"]:
                continue
            delta = np.abs(np.array(row["roi"]["center_xy_m"], dtype=float) - focus)
            if (abs(delta[0] - SPACING) < 1e-6 and delta[1] < 1e-6) or (abs(delta[1] - SPACING) < 1e-6 and delta[0] < 1e-6):
                neighbors += 1
        same_frame = sum(1 for other in eligible if other["frame_token"] == case["frame_token"])
        ranked.append((same_frame > 1, -neighbors, case["frame_token"], case["roi_id"], case))
    ranked.sort(key=lambda item: item[:4])
    return ranked[0][-1]


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    checked = audit_files()
    packs, reasons, geometry, expert = policy_arrays(checked)
    rows = [summarize(packs[method], method) for method in METHODS]
    published = json.loads((EVAL / "metrics.json").read_text(encoding="utf-8"))
    for fresh, old in zip(rows, published["policies"]):
        for key in ("mean_error", "r2", "r3", "joint_false_positives", "joint_false_negatives", "corrections", "introduced_errors"):
            if abs(float(fresh[key]) - float(old[key])) > 1e-12:
                raise SystemExit(f"AUDIT_METRIC_MISMATCH {fresh['method']} {key}")
    stock = list(csv.DictReader((EVAL / "stock_study" / "comparison.csv").open(encoding="utf-8")))
    stock_by = {row["method"]: row for row in stock}
    offline_to_stock = {"local": "local_only", "majority": "majority", "conservative_f0": "f0_0.900"}
    for method, stock_name in offline_to_stock.items():
        fresh = next(row for row in rows if row["method"] == method)
        reference = stock_by[stock_name]
        if abs(fresh["mean_error"] - float(reference["marginal_error"])) > 1e-12:
            raise SystemExit(f"AUDIT_STOCK_MISMATCH {method}")
        if fresh["corrections"] != int(reference["corrected_agent_decisions"]):
            raise SystemExit(f"AUDIT_STOCK_CORRECTIONS {method}")
        if fresh["introduced_errors"] != int(reference["new_agent_errors"]):
            raise SystemExit(f"AUDIT_STOCK_INTRODUCED {method}")
    majority = np.concatenate([item[2] for item in packs["majority"]])
    weighted = np.concatenate([item[2] for item in packs["weighted"]])
    f0 = np.concatenate([item[2] for item in packs["conservative_f0"]])
    override = np.concatenate([item[2] for item in packs["expert_override"]])
    always = np.concatenate([item[2] for item in packs["always_a"]])
    local = np.concatenate([item[1] for item in packs["local"]])
    if not np.array_equal(majority, weighted):
        raise SystemExit("AUDIT_WEIGHTED_DIFFERS")
    if not np.array_equal(f0, override):
        raise SystemExit("AUDIT_OVERRIDE_DIFFERS")
    if not np.array_equal(always, np.repeat(local[:, 2:3], 3, axis=1)):
        raise SystemExit("AUDIT_ALWAYS_A_DIFFERS")
    truth = np.concatenate([item[0] for item in packs["local"]])
    transitions = {
        method: transition_table(
            truth,
            local,
            np.concatenate([item[2] for item in packs[method]]),
        )
        for method in METHODS if method != "local"
    }
    patterns = classify_patterns(packs, reasons)
    cases = lost_cases(packs, geometry)
    both_case = choose_case(cases, checked["frames"], True)
    kept_case = choose_case(cases, checked["frames"], False)
    draw_case(
        both_case, checked["frames"][both_case["frame_token"]], FIG / "lost_detection_majority_and_f0.png",
        f"Frame {both_case['frame_token']} {both_case['roi_id']}: vehicle {both_case['vehicle']} was correct and both policies erased it",
    )
    draw_case(
        kept_case, checked["frames"][kept_case["frame_token"]], FIG / "lost_detection_majority_only.png",
        f"Frame {kept_case['frame_token']} {kept_case['roi_id']}: vehicle {kept_case['vehicle']} was correct; F0 kept the local label",
    )
    draw_map(cases, checked["frames"], FIG / "lost_detection_locations.png")
    spatial = dependence(checked["frames"])
    blocks = {str(length): block_bootstrap(packs, length, BOOTSTRAP_SEED, BOOTSTRAP_DRAWS) for length in BLOCK_LENGTHS}
    for method in METHODS:
        if method == "local":
            continue
        for key in ("mean_error", "r2", "r3"):
            published_band = published["bootstrap_versus_local"][method][key]
            fresh_band = blocks["1"][method][key]
            if any(abs(a - b) > 1e-12 for a, b in zip(published_band, fresh_band)):
                raise SystemExit(f"AUDIT_BLOCK1_BOOTSTRAP_MISMATCH {method} {key}")
    payload = {
        "expert": expert,
        "file_audit": {key: value for key, value in checked.items() if key not in {"predictions", "frames", "manifest"}},
        "policies": rows,
        "transitions": transitions,
        "f0_acceptance_by_who_is_wrong": patterns,
        "lost_correct_detections": cases,
        "illustrated_cases": {"majority_and_f0": both_case, "majority_only": kept_case},
        "dependence": spatial,
        "block_bootstrap": blocks,
        "frozen_protocol_changed": False,
        "detector_inference_rerun": False,
        "octopus_source_modified": False,
    }
    (HERE / "audit_summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "rows": payload["file_audit"]["rows"],
        "lost_correct_detections": len(cases),
        "lost_by_f0": sum(case["lost_by_f0"] for case in cases),
        "figures": [
            "lost_detection_majority_and_f0.png",
            "lost_detection_majority_only.png",
            "lost_detection_locations.png",
        ],
        "block_lengths": list(BLOCK_LENGTHS),
    }, indent=2))


if __name__ == "__main__":
    main()
