"""Score the frozen CooperScene export with the existing OCTOPUS study.

This file does not modify Octopus-main. It calls convert_to_trace and
perform_evaluation, then scores the P1 baselines those two entry points do not
all emit. Reliability rates are read from the manifest, which was filled from
validation regions. The expert is the vehicle with the smallest of those rates.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4] / "Octopus-main"
sys.path.insert(0, str(ROOT))

from octopus_fusion.contracts import (  # noqa: E402
    AgentEvidence, FusionConfig, FusionObservation, ReliabilityEstimate,
)
from octopus_fusion.fusion import SelectiveFuser  # noqa: E402
from octopus_sim.datasets.three_vehicle_real import convert_to_trace  # noqa: E402
from scripts.run_three_agent_tradeoff_frontier import (  # noqa: E402
    AlwaysVote, DiagnosticExpertOverride,
)
from scripts.run_three_vehicle_real_study import perform_evaluation  # noqa: E402

AGENTS = ("1", "2", "3")
EXPORT = Path(__file__).resolve().parents[1] / "test_inference"
OUT = Path(__file__).resolve().parent
PREPARED = OUT / "prepared"
STOCK = OUT / "stock_study"
BOOTSTRAP_SEED = 77109 + 123
BOOTSTRAP_DRAWS = 2000
P1_TABLE = {
    "local": {"mean_error": 0.20025, "r2": 0.19800, "r3": 0.00200},
    "majority": {"mean_error": 0.19800, "r2": 0.19800, "r3": 0.19800},
    "conservative_f0": {"mean_error": 0.13658, "r2": 0.19800, "r3": 0.00400},
    "expert_override": {"mean_error": 0.01375, "r2": 0.01375, "r3": 0.01375},
}


def require_export() -> Path:
    needed = [
        "predictions.jsonl", "manifest.json", "ground_truth.jsonl",
        "vehicle_1_predictions.jsonl", "vehicle_2_predictions.jsonl",
        "vehicle_3_predictions.jsonl",
    ]
    missing = [name for name in needed if not (EXPORT / name).is_file()]
    if missing:
        raise SystemExit("MISSING_EXPORT " + " ".join(missing))
    return EXPORT


def verify_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    if manifest.get("dataset") != "CooperScene":
        problems.append("dataset")
    if manifest.get("split") != "test":
        problems.append("split")
    if manifest.get("vehicle_ids") != ["1", "2", "3"]:
        problems.append("vehicle_ids")
    if manifest.get("prediction_origin") != "real_detector_export":
        problems.append("origin")
    if manifest.get("coordinate_frame") != "cooperscene_global_xy_m":
        problems.append("frame")
    runs = manifest.get("physical_detector_runs") or {}
    if set(runs) != set(AGENTS) or len(set(runs.values())) != 3:
        problems.append("run_ids")
    rates = manifest.get("assumed_source_error") or {}
    if set(rates) != set(AGENTS):
        problems.append("rates")
    note = manifest.get("error_rate_note", "")
    if "validation" not in note or "not object-level F1" not in note:
        problems.append("rate_note")
    if problems:
        raise SystemExit("MANIFEST_REJECTED " + ",".join(problems))
    return manifest


def expert_from_validation(rates: dict) -> str:
    return min(AGENTS, key=lambda agent: (float(rates[agent]), agent))


def load_trace(path: Path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    frames = defaultdict(list)
    order = []
    for row in rows:
        if row["frame_id"] not in frames:
            order.append(row["frame_id"])
        frames[row["frame_id"]].append(row)
    return rows, [frames[frame] for frame in order]


def observation(row: dict, shared_lineage: bool) -> FusionObservation:
    frame = row["frame_id"]
    evidence = []
    for agent in AGENTS:
        evidence.append(AgentEvidence(
            agent,
            int(row["candidates"][f"local:{agent}"]),
            f"result:{frame}:{agent}",
            "shared_scene" if shared_lineage else f"physical_vehicle_{agent}",
            15.0,
        ))
    return FusionObservation(row["event_id"], frame, 20.0, tuple(evidence), 0.5)


def reliability(rates: dict) -> ReliabilityEstimate:
    return ReliabilityEstimate(
        tuple((agent, float(rates[agent])) for agent in AGENTS),
        "validation_region_error_not_object_f1",
    )


def study_config(scenario: dict) -> FusionConfig:
    block = scenario["fusion_f0"]
    return FusionConfig(
        max_source_error=float(block["max_source_error"]),
        max_age_ms=float(block["max_age_ms"]),
        dependence_discount=float(block["dependence_discount"]),
        min_independent_groups=int(block["min_independent_groups"]),
        min_supporting_groups=int(block["min_supporting_groups"]),
        max_conflict_fraction=float(block["max_conflict_fraction"]),
        min_score_confidence=float(block["min_score_confidence"]),
    )


def decide_all(frame_rows, method: str, fusers: dict, rates: dict, expert: str, shared_lineage: bool):
    q = reliability(rates)
    local = []
    truth = []
    final = []
    accepted = []
    for row in frame_rows:
        labels = np.array([int(row["candidates"][f"local:{agent}"]) for agent in AGENTS], dtype=int)
        local.append(labels)
        truth.append(int(row["truth"]))
        if method == "local":
            final.append(labels.copy())
            accepted.append(False)
            continue
        if method == "always_a":
            index = AGENTS.index(expert)
            final.append(np.full(3, labels[index], dtype=int))
            accepted.append(True)
            continue
        decision = fusers[method].decide(observation(row, shared_lineage), q)
        final.append(np.array([dict(decision.per_agent_decisions)[agent] for agent in AGENTS], dtype=int))
        accepted.append(bool(decision.shared))
    return np.array(truth), np.stack(local), np.stack(final), np.array(accepted)


def event_counts(truth, labels):
    wrong = labels != truth[:, None]
    positive = truth == 1
    negative = ~positive
    return {
        "n_events": int(len(truth)),
        "n_labels": int(labels.size),
        "mean_error": float(wrong.mean()) if len(truth) else None,
        "r2": float((wrong.sum(axis=1) >= 2).mean()) if len(truth) else None,
        "r3": float(wrong.all(axis=1).mean()) if len(truth) else None,
        "joint_false_positives": int((negative & (labels == 1).all(axis=1)).sum()),
        "joint_false_negatives": int((positive & (labels == 0).all(axis=1)).sum()),
    }


def paired(truth, local, final):
    local_wrong = local != truth[:, None]
    final_wrong = final != truth[:, None]
    return {
        "corrections": int((local_wrong & ~final_wrong).sum()),
        "introduced_errors": int((~local_wrong & final_wrong).sum()),
    }


def correlations(truth, local):
    wrong = local != truth[:, None]
    pairs = {}
    for i, left in enumerate(AGENTS):
        for right in AGENTS[i + 1:]:
            j = AGENTS.index(right)
            if wrong[:, i].std() == 0 or wrong[:, j].std() == 0:
                value = None
            else:
                value = float(np.corrcoef(wrong[:, i], wrong[:, j])[0, 1])
            pairs[f"{left}_{right}"] = value
    return pairs


def summarize(frame_pack, method: str):
    truth = np.concatenate([item[0] for item in frame_pack])
    local = np.concatenate([item[1] for item in frame_pack])
    final = np.concatenate([item[2] for item in frame_pack])
    accepted = np.concatenate([item[3] for item in frame_pack])
    counts = event_counts(truth, final)
    counts.update(paired(truth, local, final))
    counts["accepted_fraction"] = float(accepted.mean()) if len(accepted) else None
    counts["method"] = method
    return counts


def bootstrap(frame_pack, seed: int, draws: int):
    rng = np.random.default_rng(seed)
    n = len(frame_pack)
    deltas = {key: [] for key in ("mean_error", "r2", "r3")}
    for _ in range(draws):
        pick = rng.integers(0, n, n)
        chosen = [frame_pack[index] for index in pick]
        policy = summarize(chosen, "policy")
        local = event_counts(
            np.concatenate([item[0] for item in chosen]),
            np.concatenate([item[1] for item in chosen]),
        )
        for key in deltas:
            deltas[key].append(policy[key] - local[key])
    out = {"draws": draws, "seed": seed, "frames": n}
    for key, values in deltas.items():
        array = np.asarray(values)
        out[key] = [float(np.quantile(array, 0.025)), float(np.quantile(array, 0.975))]
    return out


def fusers_for(config: FusionConfig, expert: str) -> dict:
    strict = SelectiveFuser(config)
    return {
        "majority": AlwaysVote("majority"),
        "weighted": AlwaysVote("weighted"),
        "conservative_f0": strict,
        "expert_override": DiagnosticExpertOverride(SelectiveFuser(config), expert=expert),
    }


def write_table(path: Path, rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def findings(manifest, expert, rows, intervals, corr, shared_rows, stock_rows) -> str:
    by = {row["method"]: row for row in rows}
    lines = [
        "# CooperScene three-vehicle evaluation",
        "",
        "The frozen protocol was not changed. Octopus-main was not edited.",
        "Reliability rates are the validation region-error rates stored in the manifest.",
        "They are not object-level F1, and they were not refit on the test split.",
        f"The predeclared expert is vehicle {expert}, the lowest validation rate.",
        "Ties would break toward the smaller vehicle id. Test performance was not used.",
        "",
        "Distinct result IDs were checked as three different strings.",
        "That check does not establish statistically independent errors.",
        "The pairwise correlations below are the local detectors' error indicators.",
        "",
        "## Verification",
        "",
        "The existing `convert_to_trace` accepted the export: three vehicles, synchronized region identities, one shared truth file, and matching per-vehicle files.",
        "The existing `perform_evaluation` then ran local, majority, and the F0 threshold list.",
        "",
        "## Policies",
        "",
        "| Policy | Mean error | R2 | R3 | Joint false alarms | Joint misses | Corrections | Introduced errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for method in ("local", "majority", "weighted", "conservative_f0", "expert_override", "always_a"):
        row = by[method]
        lines.append(
            f"| {method} | {row['mean_error']:.4f} | {row['r2']:.4f} | {row['r3']:.4f} | "
            f"{row['joint_false_positives']} | {row['joint_false_negatives']} | "
            f"{row['corrections']} | {row['introduced_errors']} |"
        )
    lines.extend(["", "## Frame bootstrap versus local", "",
                   f"Seed {BOOTSTRAP_SEED}, {BOOTSTRAP_DRAWS} draws, resampling the {intervals['local']['frames']} physical frames.",
                   "The interval is the 2.5 and 97.5 percentiles of the paired difference.",
                   ""])
    lines.append("| Policy minus local | Mean error | R2 | R3 |")
    lines.append("|---|---|---|---|")
    for method, band in intervals.items():
        if method == "local":
            continue
        lines.append(
            f"| {method} | [{band['mean_error'][0]:+.4f}, {band['mean_error'][1]:+.4f}] | "
            f"[{band['r2'][0]:+.4f}, {band['r2'][1]:+.4f}] | "
            f"[{band['r3'][0]:+.4f}, {band['r3'][1]:+.4f}] |"
        )
    lines.extend(["", "## Local error correlation", ""])
    for pair, value in corr.items():
        shown = "undefined" if value is None else f"{value:.4f}"
        lines.append(f"- Vehicles {pair.replace('_', ' and ')}: {shown}")
    lines.extend(["", "## One shared lineage", "",
                   "Repeating conservative F0 with all three vehicles in one dependence group removes the assumption that distinct result IDs are independent evidence.",
                   ""])
    for row in shared_rows:
        lines.append(
            f"- {row['method']}: mean error {row['mean_error']:.4f}, R2 {row['r2']:.4f}, "
            f"R3 {row['r3']:.4f}, accepted fraction {row['accepted_fraction']:.4f}"
        )
    lines.extend(["", "## Existing study script", ""])
    for row in stock_rows:
        lines.append(
            f"- {row['method']}: mean error {row['marginal_error']:.4f}, "
            f"R2 {row['r_ge_2']:.4f}, R3 {row['r_ge_3']:.4f}"
        )
    lines.extend(["", "## Against the P1 synthetic three-agent result", "",
                   "P1 Table 3, shock 0.18, seed 77109, 4,000 queries:",
                   "local mean error 0.2003, R2 0.1980, R3 0.0020;",
                   "majority 0.1980, 0.1980, 0.1980;",
                   "conservative F0 0.1366, 0.1980, 0.0040;",
                   "expert override 0.0138, 0.0138, 0.0138, and on that draw it copied A on every query.",
                   "F0 there lowered mean error and left R2 unchanged, while majority turned R2 into R3.",
                   "The expert result depended on a declared error of 1.5 percent. The override rule does not fire above 5 percent.",
                   "Compare the table above with those signs rather than with the synthetic percentages.",
                   ""])
    q = manifest["assumed_source_error"]
    lines.append(
        "Validation rates used here: "
        + ", ".join(f"vehicle {agent} {float(q[agent]):.6f}" for agent in AGENTS)
        + "."
    )
    if float(q[expert]) > 0.05:
        lines.append(
            f"Vehicle {expert}'s validation rate is above 0.05, so the P1 expert override does not engage. "
            "It is reported anyway, and it should match conservative F0. Always-A still copies that vehicle on every region."
        )
    lines.append(
        "Energy and latency from the stock script remain the hypothetical E1 profile."
    )
    return "\n".join(lines) + "\n"


def run(export: Path):
    manifest = verify_manifest(export / "manifest.json")
    expert = expert_from_validation(manifest["assumed_source_error"])
    PREPARED.mkdir(parents=True, exist_ok=True)
    provenance = convert_to_trace(export / "predictions.jsonl", export / "manifest.json", PREPARED)
    if provenance["physical_vehicles"] != ["1", "2", "3"]:
        raise SystemExit("PREPARE_REJECTED vehicles")
    if len(set(manifest["physical_detector_runs"].values())) != 3:
        raise SystemExit("PREPARE_REJECTED run ids")
    stock = perform_evaluation(PREPARED / "scenario.json", STOCK)
    scenario = json.loads((PREPARED / "scenario.json").read_text(encoding="utf-8"))
    config = study_config(scenario)
    built = fusers_for(config, expert)
    _rows, frames = load_trace(PREPARED / "trace.jsonl")
    rates = manifest["assumed_source_error"]
    methods = ("local", "majority", "weighted", "conservative_f0", "expert_override", "always_a")
    packs = {method: [] for method in methods}
    for frame in frames:
        truth, local, _final, _accepted = decide_all(frame, "local", built, rates, expert, False)
        packs["local"].append((truth, local, local, np.zeros(len(frame), dtype=bool)))
        for method in methods:
            if method == "local":
                continue
            truth, local, final, accepted = decide_all(frame, method, built, rates, expert, False)
            packs[method].append((truth, local, final, accepted))
    rows = [summarize(packs[method], method) for method in methods]
    intervals = {"local": {"frames": len(frames), "mean_error": [0, 0], "r2": [0, 0], "r3": [0, 0]}}
    for method in methods:
        if method == "local":
            continue
        intervals[method] = bootstrap(packs[method], BOOTSTRAP_SEED, BOOTSTRAP_DRAWS)
    pooled_truth = np.concatenate([item[0] for item in packs["local"]])
    pooled_local = np.concatenate([item[1] for item in packs["local"]])
    corr = correlations(pooled_truth, pooled_local)
    shared = []
    for method in ("conservative_f0", "expert_override"):
        pack = []
        for frame in frames:
            truth, local, final, accepted = decide_all(frame, method, built, rates, expert, True)
            pack.append((truth, local, final, accepted))
        shared.append(summarize(pack, method + "_shared_lineage"))
    payload = {
        "expert": expert,
        "validation_rates": {agent: float(rates[agent]) for agent in AGENTS},
        "policies": rows,
        "bootstrap_versus_local": intervals,
        "local_error_correlation": corr,
        "shared_lineage": shared,
        "stock_study": [
            {key: row[key] for key in ("method", "marginal_error", "r_ge_2", "r_ge_3")}
            for row in stock
        ],
        "p1_table3_reference": P1_TABLE,
        "distinct_run_ids_are_not_independence": True,
        "frozen_protocol_changed": False,
        "octopus_source_modified": False,
    }
    (OUT / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_table(OUT / "metrics.csv", rows)
    text = findings(manifest, expert, rows, intervals, corr, shared, stock)
    (OUT / "FINDINGS.md").write_text(text, encoding="utf-8")
    print(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        print("SELF_CHECK_SKIPPED_USE_REAL_EXPORT")
        return
    require_export()
    run(EXPORT)


if __name__ == "__main__":
    main()
