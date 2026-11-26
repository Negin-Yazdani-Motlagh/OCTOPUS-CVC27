#!/usr/bin/env python3
"""P0 acceptance tables that were not in the earlier sequence CSVs.

Reads the regenerated nine-sequence trace. Does not modify OCTOPUS-Sim.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

TRACE = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P0/v2v4real_all/trace.jsonl")
PROV = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P0/v2v4real_all/provenance.jsonl")
OUT = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P0/acceptance_audit")

BROADCAST = (
    "late_fusion", "disagreement_gate", "OR", "AND",
    "always_cobevt", "always_ego", "always_partner",
)
SEED = 20261118
REPS = 20000
BLOCKS = (1, 6, 12, 24)


def broadcast_bit(query: dict, policy: str) -> int:
    ego, partner, late = query["ego"], query["partner"], query["late"]
    if policy == "always_ego":
        return ego
    if policy == "always_partner":
        return partner
    if policy == "late_fusion":
        return late
    if policy == "always_cobevt":
        return query["cobevt"]
    if policy == "OR":
        return max(ego, partner)
    if policy == "AND":
        return min(ego, partner)
    if policy == "disagreement_gate":
        return late if ego != partner else ego
    raise KeyError(policy)


def load_frames() -> dict[str, list[dict]]:
    provenance = {row["event_id"]: row for row in map(json.loads, PROV.read_text().splitlines())}
    grouped: dict[tuple[str, int], dict] = defaultdict(dict)
    for event in map(json.loads, TRACE.read_text().splitlines()):
        meta = provenance[event["event_id"]]
        late = int(event["candidates"]["edge:ego"])
        if int(event["candidates"]["edge:agent1"]) != late:
            raise ValueError(event["event_id"])
        grouped[(meta["scene_id"], int(meta["frame_id"]))][meta["roi"]] = {
            "truth": int(event["truth"]),
            "ego": int(event["candidates"]["local:ego"]),
            "partner": int(event["candidates"]["local:agent1"]),
            "late": late,
            "cobevt": int(meta["cobevt_candidate"]),
        }
    scenes: dict[str, list[dict]] = defaultdict(list)
    for (scene, frame), queries in sorted(grouped.items()):
        if set(queries) != {"positive", "negative"}:
            raise ValueError((scene, frame, set(queries)))
        scenes[scene].append({"frame": frame, **queries})
    return scenes


def outcome_class(local_joint: bool, shared_wrong: bool) -> str:
    if local_joint and shared_wrong:
        return "both_fail"
    if local_joint:
        return "rescued_joint_failure"
    if shared_wrong:
        return "introduced_joint_failure"
    return "both_success"


def write_csv(path: Path, rows: list[dict]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def paired_rows(scenes: dict[str, list[dict]]) -> list[dict]:
    rows = []
    classes = ("both_success", "rescued_joint_failure", "introduced_joint_failure", "both_fail")
    for scene, frames in list(scenes.items()) + [("all", [frame for frames in scenes.values() for frame in frames])]:
        queries = [frame[roi] for frame in frames for roi in ("positive", "negative")]
        for policy in BROADCAST:
            for subset_name, subset in (
                ("all", queries),
                ("positive", [query for query in queries if query["truth"] == 1]),
                ("negative", [query for query in queries if query["truth"] == 0]),
            ):
                counts = {name: 0 for name in classes}
                agent_errors = corrected = introduced = 0
                fully_correct_frames = 0
                if subset_name == "all":
                    for frame in frames:
                        frame_ok = True
                        for roi in ("positive", "negative"):
                            bit = broadcast_bit(frame[roi], policy)
                            frame_ok = frame_ok and bit == frame[roi]["truth"]
                        fully_correct_frames += int(frame_ok)
                for query in subset:
                    truth = query["truth"]
                    bit = broadcast_bit(query, policy)
                    local_joint = query["ego"] != truth and query["partner"] != truth
                    counts[outcome_class(local_joint, bit != truth)] += 1
                    agent_errors += 2 * int(bit != truth)
                    for source in (query["ego"], query["partner"]):
                        corrected += int(source != truth and bit == truth)
                        introduced += int(source == truth and bit != truth)
                row = {
                    "sequence": scene,
                    "policy": policy,
                    "query_class": subset_name,
                    "queries": len(subset),
                    "frames": len(frames) if subset_name == "all" else "",
                    "frames_with_both_queries": len(frames) if subset_name == "all" else "",
                    "frames_both_queries_correct": fully_correct_frames if subset_name == "all" else "",
                    "agent_labels": 2 * len(subset),
                    "agent_errors": agent_errors,
                    "mean_error": agent_errors / (2 * len(subset)),
                    "corrected_labels": corrected,
                    "introduced_labels": introduced,
                }
                row.update(counts)
                if sum(counts.values()) != len(subset):
                    raise AssertionError(scene)
                rows.append(row)
    check = next(row for row in rows if row["sequence"] == "0007" and row["policy"] == "late_fusion" and row["query_class"] == "all")
    expected = {"both_success": 426, "introduced_joint_failure": 12, "rescued_joint_failure": 0, "both_fail": 4}
    if {key: check[key] for key in expected} != expected:
        raise AssertionError(check)
    return rows


def frame_matrix(frames: list[dict]) -> np.ndarray:
    """Columns: local, late, gate, OR, AND, cobevt, ego, partner. Each policy has errors, r2, fn, fp."""
    columns = []
    for frame in frames:
        values = []
        for policy, kind in (
            ("local", "pair"),
            ("late_fusion", "broadcast"),
            ("disagreement_gate", "broadcast"),
            ("OR", "broadcast"),
            ("AND", "broadcast"),
            ("always_cobevt", "broadcast"),
            ("always_ego", "broadcast"),
            ("always_partner", "broadcast"),
        ):
            errors = r2 = fn = fp = 0
            for roi, query in (("positive", frame["positive"]), ("negative", frame["negative"])):
                truth = query["truth"]
                if kind == "pair":
                    wrongs = (query["ego"] != truth, query["partner"] != truth)
                    errors += sum(wrongs)
                    both = int(all(wrongs))
                else:
                    bit = broadcast_bit(query, policy)
                    both = int(bit != truth)
                    errors += 2 * both
                r2 += both
                fn += int(roi == "positive" and both)
                fp += int(roi == "negative" and both)
            values.extend((errors, r2, fn, fp))
        columns.append(values)
    return np.asarray(columns, dtype=np.int32)


def bootstrap(scenes: dict[str, list[dict]]) -> tuple[list[dict], list[dict]]:
    matrices = {scene: frame_matrix(frames) for scene, frames in scenes.items()}
    names = ("local", "late_fusion", "disagreement_gate", "OR", "AND", "always_cobevt", "always_ego", "always_partner")
    metrics = ("mean_error", "r2", "joint_fn", "joint_fp")
    # column layout: 8 policies * 4 metrics
    contrasts = (
        ("late_fusion", "local"),
        ("disagreement_gate", "local"),
        ("always_ego", "local"),
        ("always_partner", "local"),
        ("always_ego", "late_fusion"),
        ("always_partner", "late_fusion"),
        ("late_fusion", "always_ego"),
    )
    denom = {"mean_error": 4, "r2": 2, "joint_fn": 1, "joint_fp": 1}
    rng = np.random.default_rng(SEED)
    pooled_rows = []
    sequence_rows = []

    def rates(total: np.ndarray, frames: int) -> dict[tuple[str, str], float]:
        out = {}
        for policy_index, policy in enumerate(names):
            for metric_index, metric in enumerate(metrics):
                numerator = total[policy_index * 4 + metric_index]
                out[(policy, metric)] = float(numerator) / (frames * denom[metric])
        return out

    def summarize(draws: np.ndarray, point: float) -> dict[str, float]:
        low, high = np.quantile(draws, [0.025, 0.975])
        return {
            "point": point,
            "ci_low": float(low),
            "ci_high": float(high),
            "replicates_below_zero": int((draws < 0).sum()),
            "replicates_zero": int((draws == 0).sum()),
            "replicates_above_zero": int((draws > 0).sum()),
        }

    # Sequence-cluster bootstrap for the new baselines, same seed as the earlier study.
    scene_names = list(matrices)
    scene_totals = np.stack([matrix.sum(axis=0) for matrix in matrices.values()])
    scene_frames = np.array([matrix.shape[0] for matrix in matrices.values()])
    picks = rng.integers(0, len(scene_names), size=(REPS, len(scene_names)))
    sampled_totals = scene_totals[picks].sum(axis=1)
    sampled_frames = scene_frames[picks].sum(axis=1)
    observed_frames = int(scene_frames.sum())
    observed = rates(scene_totals.sum(axis=0), observed_frames)
    for left, right in contrasts:
        for metric in metrics:
            draws = np.zeros(REPS)
            for policy, sign in ((left, 1.0), (right, -1.0)):
                index = names.index(policy) * 4 + metrics.index(metric)
                draws += sign * sampled_totals[:, index] / (sampled_frames * denom[metric])
            point = observed[(left, metric)] - observed[(right, metric)]
            pooled_rows.append({
                "design": "sequence_cluster",
                "block_length_frames": "",
                "contrast": f"{left} - {right}",
                "metric": metric,
                "replicates": REPS,
                "seed": SEED,
                **summarize(draws, point),
            })

    for block in BLOCKS:
        pooled_draws = {(left, right, metric): np.zeros(REPS) for left, right in contrasts for metric in metrics}
        for scene, matrix in matrices.items():
            frame_count = matrix.shape[0]
            n_blocks = int(np.ceil(frame_count / block))
            scene_draw = np.zeros((REPS, matrix.shape[1]), dtype=np.int64)
            for start_rep in range(0, REPS, 500):
                stop = min(REPS, start_rep + 500)
                starts = rng.integers(0, frame_count, size=(stop - start_rep, n_blocks))
                offsets = (starts[..., None] + np.arange(block)) % frame_count
                chosen = offsets.reshape(stop - start_rep, n_blocks * block)[:, :frame_count]
                scene_draw[start_rep:stop] = matrix[chosen].sum(axis=1)
            point_scene = rates(matrix.sum(axis=0), frame_count)
            for left, right in contrasts:
                for metric in metrics:
                    left_index = names.index(left) * 4 + metrics.index(metric)
                    right_index = names.index(right) * 4 + metrics.index(metric)
                    draws = (scene_draw[:, left_index] - scene_draw[:, right_index]) / (frame_count * denom[metric])
                    pooled_draws[(left, right, metric)] += draws * frame_count
                    if block in (1, 12, 24):
                        sequence_rows.append({
                            "sequence": scene,
                            "frames": frame_count,
                            "block_length_frames": block,
                            "contrast": f"{left} - {right}",
                            "metric": metric,
                            "replicates": REPS,
                            "seed": SEED,
                            **summarize(draws, point_scene[(left, metric)] - point_scene[(right, metric)]),
                        })
        for left, right in contrasts:
            for metric in metrics:
                draws = pooled_draws[(left, right, metric)] / observed_frames
                point = observed[(left, metric)] - observed[(right, metric)]
                pooled_rows.append({
                    "design": "within_sequence_circular_block",
                    "block_length_frames": block,
                    "contrast": f"{left} - {right}",
                    "metric": metric,
                    "replicates": REPS,
                    "seed": SEED,
                    **summarize(draws, point),
                })
        print("block", block, flush=True)
    return pooled_rows, sequence_rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scenes = load_frames()
    if [len(frames) for frames in scenes.values()] != [147, 114, 144, 198, 180, 310, 304, 221, 375]:
        raise AssertionError([len(frames) for frames in scenes.values()])
    rows = paired_rows(scenes)
    write_csv(OUT / "paired_outcome_transitions.csv", rows)
    write_csv(OUT / "always_source_baselines.csv", [row for row in rows if row["policy"] in ("always_ego", "always_partner")])
    pooled, by_sequence = bootstrap(scenes)
    write_csv(OUT / "temporal_block_bootstrap.csv", pooled)
    write_csv(OUT / "temporal_block_by_sequence.csv", by_sequence)
    (OUT / "method.json").write_text(json.dumps({
        "trace": str(TRACE),
        "paired_classes": ["both_success", "rescued_joint_failure", "introduced_joint_failure", "both_fail"],
        "class_definition": "local joint failure versus the broadcast label on the same query",
        "always_ego": "both agents receive the ego detector label",
        "always_partner": "both agents receive the partner detector label",
        "complete_frame": "both the positive and negative queries are correct under the broadcast label",
        "bootstrap_seed": SEED,
        "bootstrap_replicates": REPS,
        "block_lengths_frames": list(BLOCKS),
        "block_design": "each sequence is resampled to its own length with a circular moving block; the two queries in a frame stay together; sequences are not mixed",
        "sequence_cluster_design": "nine sequences drawn with replacement, same seed, size-weighted pooled rate",
        "interval": "2.5 and 97.5 percentiles, numpy quantile linear",
    }, indent=2) + "\n", encoding="utf-8")
    print("sequences", {scene: len(frames) for scene, frames in scenes.items()})


if __name__ == "__main__":
    main()
