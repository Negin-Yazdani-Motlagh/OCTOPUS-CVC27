#!/usr/bin/env python3
"""Finish the remaining P1 mechanism checks without editing Octopus-main.

Six paired seeds of the original five-agent correlation sweep, equal true and
assumed error 0.10, and a separate comparison of shared result IDs against
correlated error draws.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path("/Users/negin/UML/Mobihoc_Extention/Octopus-main")
sys.path.insert(0, str(ROOT))

import numpy as np
from octopus_fusion.contracts import AgentEvidence, FusionConfig, FusionObservation, ReliabilityEstimate
from octopus_fusion.fusion import SelectiveFuser
from scripts.run_f0_cvc_parameter_study import (
    AGENTS as FIVE,
    RHOS,
    TRUE_Q,
    NaiveVoteFuser,
    _frame_group_arrays,
    boot_ci,
    fast_study_run,
    generate_controlled_traces,
    summarize_local,
)

OUT = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P1/remaining_mechanisms")
SEEDS = (5701, 5702, 5703, 5704, 5705, 5706)
FRAMES = 2000
ROIS = 2
BOOT = 2500
Q_EQUAL = 0.10
THREE = ("a", "b", "c")
F0 = FusionConfig(
    max_source_error=0.49, min_score_confidence=0.90, min_independent_groups=2,
    min_supporting_groups=2, max_conflict_fraction=0.40, dependence_discount=1.0,
    max_age_ms=120.0,
)


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(rows[0])
    for row in rows[1:]:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, restval="")
        writer.writeheader()
        writer.writerows(rows)


def indices_for(seed: int) -> np.ndarray:
    return np.random.default_rng(seed + 109).integers(0, FRAMES, size=(BOOT, FRAMES), dtype=np.int32)


def clusters(wrong: np.ndarray) -> dict[str, np.ndarray]:
    count = wrong.sum(axis=2)
    out = {"mean": wrong.mean(axis=(1, 2))}
    for m in range(1, wrong.shape[2] + 1):
        out[f"r{m}"] = (count >= m).mean(axis=1)
    return out


def paired(local: np.ndarray, other: np.ndarray, draws: np.ndarray) -> tuple[float, float, float]:
    diff = other - local
    low, high = boot_ci(diff, draws)
    return float(diff.mean()), low, high


def final_predictions(agents, local_pred, method: str, groups: dict[str, str],
                      result_ids: dict[str, str], q_by_agent: dict[str, float],
                      event_id: str, frame_id: str):
    if method == "local":
        return dict(local_pred), "LOCAL", None
    evidence = tuple(
        AgentEvidence(agent, int(local_pred[agent]), result_ids[agent], groups[agent], 20.0)
        for agent in agents
    )
    observation = FusionObservation(event_id, frame_id, 31.0, evidence, 0.5)
    reliability = ReliabilityEstimate(tuple((agent, q_by_agent[agent]) for agent in agents), "configured_q")
    if method == "majority":
        fuser = NaiveVoteFuser("majority")
    elif method == "weighted":
        fuser = NaiveVoteFuser("weighted")
    elif method == "f0":
        fuser = SelectiveFuser(F0)
    else:
        raise ValueError(method)
    verdict = fuser.decide(observation, reliability)
    return dict(verdict.per_agent_decisions), verdict.action.value, verdict.fused_prediction


def evaluate_grid(truth, pred, agents, method, groups, result_for, q_by_agent):
    """pred is (frames, rois, agents) int. result_for(frame) -> dict agent->result_id."""
    wrong = np.empty(pred.shape, dtype=bool)
    actions = []
    for frame in range(pred.shape[0]):
        ids = result_for(frame)
        for roi in range(pred.shape[1]):
            local = {agent: int(pred[frame, roi, index]) for index, agent in enumerate(agents)}
            chosen, action, _ = final_predictions(
                agents, local, method, groups, ids, q_by_agent,
                f"S{frame:05d}:r{roi}", f"S{frame:05d}",
            )
            actions.append(action)
            for index, agent in enumerate(agents):
                wrong[frame, roi, index] = chosen[agent] != int(truth[frame, roi])
    return wrong, actions


def distinct_ids(agents):
    def build(frame: int):
        return {agent: f"S{frame:05d}:result:{agent}" for agent in agents}
    return build


def five_seed_sweep() -> tuple[list[dict], list[dict]]:
    rows = []
    contrasts = []
    methods = ("local_only", "naive_majority", "naive_weighted", "lineage_aware", "false_independence")
    for seed in SEEDS:
        traces = generate_controlled_traces(OUT / "traces" / f"seed_{seed}", FRAMES, ROIS, seed)
        draws = indices_for(seed)
        frame_ids = [f"S{i:05d}" for i in range(FRAMES)]
        for rho, trace in traces.items():
            local_row, local_scores = summarize_local(trace, FRAMES, ROIS)
            local_cluster = _frame_group_arrays(local_scores, frame_ids)
            cached = {"local_only": local_cluster}
            records = {"local_only": local_row}
            for method in methods[1:]:
                record, scores = fast_study_run(trace, method=method, nframes=FRAMES, rois=ROIS)
                cached[method] = _frame_group_arrays(scores, frame_ids)
                records[method] = record
            for method in methods:
                cluster = cached[method]
                row = {
                    "seed": seed, "rho": rho, "method": method,
                    "mean_error": records[method]["marginal_error"],
                    "r3": records[method]["r_ge_3"], "r5": records[method]["r_ge_5"],
                }
                for metric, column in (("mean", 5), ("r3", 2), ("r5", 4)):
                    delta, low, high = paired(local_cluster[:, column], cluster[:, column], draws)
                    row[f"{metric}_minus_local"] = delta
                    row[f"{metric}_low"] = low
                    row[f"{metric}_high"] = high
                rows.append(row)
                if abs(rho - 0.75) < 1e-12 and method != "local_only":
                    contrasts.append({
                        "seed": seed, "rho": rho, "method": method,
                        "mean_minus_local_pp": 100 * row["mean_minus_local"],
                        "mean_low_pp": 100 * row["mean_low"], "mean_high_pp": 100 * row["mean_high"],
                        "r3_minus_local_pp": 100 * row["r3_minus_local"],
                        "r3_low_pp": 100 * row["r3_low"], "r3_high_pp": 100 * row["r3_high"],
                        "r5_minus_local_pp": 100 * row["r5_minus_local"],
                        "r5_low_pp": 100 * row["r5_low"], "r5_high_pp": 100 * row["r5_high"],
                    })
        print("five-agent seed", seed, flush=True)
    return rows, contrasts


def equal_error() -> tuple[list[dict], list[dict], dict]:
    specs = {
        "three": {
            "agents": THREE,
            "groups": {
                "independent": {agent: agent for agent in THREE},
                "false_pair": {"a": "a", "b": "pair", "c": "pair"},
                "one_group": {agent: "all" for agent in THREE},
            },
            "risks": ("r2", "r3"),
        },
        "five": {
            "agents": FIVE,
            "groups": {
                "independent": {agent: agent for agent in FIVE},
                "false_clique": {"a": "a", "b": "b", "c": "clique", "d": "clique", "e": "clique"},
                "one_group": {agent: "all" for agent in FIVE},
            },
            "risks": ("r3", "r5"),
        },
    }
    rows = []
    contrasts = []
    checks = {"weighted_matches_majority": True, "one_group_matches_local": True}
    for seed in SEEDS:
        draws = indices_for(seed)
        for study, spec in specs.items():
            agents = spec["agents"]
            rng = np.random.default_rng(seed)
            truth = rng.integers(0, 2, size=(FRAMES, ROIS), dtype=np.int8)
            pred = np.bitwise_xor(truth[:, :, None], rng.random((FRAMES, ROIS, len(agents))) < Q_EQUAL)
            q_map = {agent: Q_EQUAL for agent in agents}
            cached = {}
            labels = {}
            for method in ("local", "majority", "weighted"):
                groups = spec["groups"]["independent"]
                wrong, _ = evaluate_grid(truth, pred, agents, method, groups, distinct_ids(agents), q_map)
                labels[method] = wrong
                cached[method] = clusters(wrong)
            for name, groups in spec["groups"].items():
                wrong, _ = evaluate_grid(truth, pred, agents, "f0", groups, distinct_ids(agents), q_map)
                labels[f"f0_{name}"] = wrong
                cached[f"f0_{name}"] = clusters(wrong)
            if not np.array_equal(labels["majority"], labels["weighted"]):
                checks["weighted_matches_majority"] = False
            if not np.array_equal(labels["local"], labels["f0_one_group"]):
                checks["one_group_matches_local"] = False
            for method, cluster in cached.items():
                row = {"seed": seed, "study": study, "method": method, "true_q": Q_EQUAL, "assumed_q": Q_EQUAL,
                       "mean_error": float(cluster["mean"].mean())}
                for risk in spec["risks"]:
                    row[risk] = float(cluster[risk].mean())
                    delta, low, high = paired(cached["local"][risk], cluster[risk], draws)
                    row[f"{risk}_minus_local"] = delta
                    row[f"{risk}_low"] = low
                    row[f"{risk}_high"] = high
                delta, low, high = paired(cached["local"]["mean"], cluster["mean"], draws)
                row["mean_minus_local"] = delta
                row["mean_low"] = low
                row["mean_high"] = high
                rows.append(row)
                if method != "local":
                    contrasts.append({
                        "seed": seed, "study": study, "method": method,
                        "mean_minus_local_pp": 100 * row["mean_minus_local"],
                        "mean_low_pp": 100 * row["mean_low"], "mean_high_pp": 100 * row["mean_high"],
                        **{f"{risk}_minus_local_pp": 100 * row[f"{risk}_minus_local"] for risk in spec["risks"]},
                        **{f"{risk}_low_pp": 100 * row[f"{risk}_low"] for risk in spec["risks"]},
                        **{f"{risk}_high_pp": 100 * row[f"{risk}_high"] for risk in spec["risks"]},
                    })
        print("equal-q seed", seed, flush=True)
    return rows, contrasts, checks


def load_predictions(path: Path):
    truth = np.empty((FRAMES, ROIS), dtype=np.int8)
    pred = np.empty((FRAMES, ROIS, 5), dtype=np.int8)
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        frame = int(row["frame_id"][1:])
        roi = int(row["event_id"].split(":r")[1])
        truth[frame, roi] = row["truth"]
        for index, agent in enumerate(FIVE):
            pred[frame, roi, index] = row["candidates"][f"local:{agent}"]
    return truth, pred


def result_reuse(five_rows: list[dict]) -> tuple[list[dict], list[dict], dict]:
    q_map = {agent: TRUE_Q[index] for index, agent in enumerate(FIVE)}
    correct = {"a": "a", "b": "b", "c": "clique", "d": "clique", "e": "clique"}
    incorrect = {agent: agent for agent in FIVE}
    rows = []
    contrasts = []
    identical_decisions = True
    rejections = 0
    rejection_error = ""
    for seed in SEEDS:
        draws = indices_for(seed)
        traces = {
            "environmental_rho_0": OUT / "traces" / f"seed_{seed}" / "synthetic_five_agent_rho_000.jsonl",
            "environmental_rho_0.75": OUT / "traces" / f"seed_{seed}" / "synthetic_five_agent_rho_075.jsonl",
            "exact_copy_rho_1": OUT / "traces" / f"seed_{seed}" / "synthetic_five_agent_rho_100.jsonl",
        }
        for mechanism, path in traces.items():
            truth, pred = load_predictions(path)
            same = (pred[:, :, 2] == pred[:, :, 3]) & (pred[:, :, 3] == pred[:, :, 4])
            cached = {}
            for method in ("local", "majority", "weighted"):
                wrong, _ = evaluate_grid(truth, pred, FIVE, method, incorrect, distinct_ids(FIVE), q_map)
                cached[method] = clusters(wrong)
            for grouping, groups in (("correct_group", correct), ("incorrect_group", incorrect)):
                wrong, actions = evaluate_grid(truth, pred, FIVE, "f0", groups, distinct_ids(FIVE), q_map)
                cached[f"f0_{grouping}"] = clusters(wrong)
                if mechanism == "exact_copy_rho_1" and grouping == "correct_group":
                    shared_wrong, shared_actions = evaluate_grid(
                        truth, pred, FIVE, "f0", correct, shared_clique_ids, q_map,
                    )
                    if not (np.array_equal(wrong, shared_wrong) and actions == shared_actions):
                        identical_decisions = False
                    cached["f0_shared_result_id"] = clusters(shared_wrong)
            if mechanism == "exact_copy_rho_1" and rejections == 0:
                rejections, rejection_error = count_illegal_groups(pred)
            for method, cluster in cached.items():
                row = {
                    "seed": seed, "mechanism": mechanism, "method": method,
                    "clique_predictions_identical": float(same.mean()),
                    "mean_error": float(cluster["mean"].mean()),
                    "r3": float(cluster["r3"].mean()), "r5": float(cluster["r5"].mean()),
                }
                for metric in ("mean", "r3", "r5"):
                    delta, low, high = paired(cached["local"][metric], cluster[metric], draws)
                    row[f"{metric}_minus_local"] = delta
                    row[f"{metric}_low"] = low
                    row[f"{metric}_high"] = high
                rows.append(row)
                if method != "local":
                    contrasts.append({
                        "seed": seed, "mechanism": mechanism, "method": method,
                        "mean_minus_local_pp": 100 * row["mean_minus_local"],
                        "r3_minus_local_pp": 100 * row["r3_minus_local"],
                        "r3_low_pp": 100 * row["r3_low"], "r3_high_pp": 100 * row["r3_high"],
                        "r5_minus_local_pp": 100 * row["r5_minus_local"],
                        "r5_low_pp": 100 * row["r5_low"], "r5_high_pp": 100 * row["r5_high"],
                    })
        print("reuse seed", seed, flush=True)
    checks = {
        "shared_result_matches_correct_group_on_exact_copy": identical_decisions,
        "illegal_shared_result_groupings": rejections,
        "illegal_grouping_error": rejection_error,
        "published_seed_environment_matches_prior_run": published_seed_matches(five_rows),
    }
    return rows, contrasts, checks


def shared_clique_ids(frame: int):
    return {
        "a": f"S{frame:05d}:result:a", "b": f"S{frame:05d}:result:b",
        "c": f"S{frame:05d}:result:shared-cde", "d": f"S{frame:05d}:result:shared-cde",
        "e": f"S{frame:05d}:result:shared-cde",
    }


def count_illegal_groups(pred: np.ndarray) -> tuple[int, str]:
    rejected = 0
    message = ""
    groups = {agent: agent for agent in FIVE}
    ids = shared_clique_ids(0)
    for roi in range(ROIS):
        local = {agent: int(pred[0, roi, index]) for index, agent in enumerate(FIVE)}
        try:
            final_predictions(FIVE, local, "f0", groups, ids, {agent: TRUE_Q[i] for i, agent in enumerate(FIVE)},
                              "illegal", "S00000")
        except ValueError as exc:
            rejected += 1
            message = str(exc)
    return rejected, message


def published_seed_matches(rows: list[dict]) -> bool:
    expected = {
        "local_only": (0.13715, 0.14525, 0.0005),
        "naive_weighted": (0.02475, 0.02475, 0.02475),
        "lineage_aware": (0.0427, 0.02475, 0.00275),
        "false_independence": (0.10055, 0.14525, 0.02),
    }
    ok = True
    for method, (mean, r3, r5) in expected.items():
        row = next(item for item in rows if item["seed"] == 5701 and abs(item["rho"] - 0.75) < 1e-12 and item["method"] == method)
        if any(abs(row[key] - value) > 1e-9 for key, value in (("mean_error", mean), ("r3", r3), ("r5", r5))):
            ok = False
    return ok


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    five_rows, five_contrasts = five_seed_sweep()
    write_csv(OUT / "five_agent_multiseed.csv", five_rows)
    write_csv(OUT / "five_agent_paired_contrasts.csv", five_contrasts)
    equal_rows, equal_contrasts, equal_checks = equal_error()
    write_csv(OUT / "equal_error_010.csv", equal_rows)
    write_csv(OUT / "equal_error_paired_contrasts.csv", equal_contrasts)
    reuse_rows, reuse_contrasts, reuse_checks = result_reuse(five_rows)
    write_csv(OUT / "result_reuse_vs_correlation.csv", reuse_rows)
    write_csv(OUT / "result_reuse_paired_contrasts.csv", reuse_contrasts)
    report = {"equal_error": equal_checks, "result_reuse": reuse_checks}
    (OUT / "invariants.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    provenance = {
        "seeds": list(SEEDS),
        "frames": FRAMES,
        "rois": ROIS,
        "bootstrap": BOOT,
        "bootstrap_seed_offset": 109,
        "five_agent_source": "scripts/run_f0_cvc_parameter_study.py generate_controlled_traces and fast_study_run",
        "equal_q": Q_EQUAL,
        "heterogeneous_q": list(TRUE_Q),
        "original_sources_modified": False,
        "previous_results_modified": False,
    }
    (OUT / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
