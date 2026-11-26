"""Sequence-clustered paired bootstrap for the nine regenerated V2V4Real traces.

Does not import or modify Octopus source. Resamples whole sequences with
replacement, then recomputes size-weighted pooled rates on the same draw for
every policy. Seed and replicate count are fixed.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

SEED = 20261118
REPS = 20000
TRACE = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P0/v2v4real_all/trace.jsonl")
OUT = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P0/statistical_analysis")

POLICIES = ("local", "late_fusion", "disagreement_gate", "OR")
CONTRASTS = (
    ("late_fusion", "local", "Late Fusion vs Local"),
    ("disagreement_gate", "local", "Disagreement Gate vs Local"),
    ("disagreement_gate", "OR", "Disagreement Gate vs OR"),
)
METRICS = (
    ("mean_error", "Mean error", "agent_errors", "agent_labels"),
    ("r2", "R2", "both_wrong", "queries"),
    ("joint_fn", "Joint false negatives", "joint_fn", "positives"),
    ("joint_fp", "Joint false positives", "joint_fp", "negatives"),
)


def labels(event: dict) -> dict[str, tuple[int, int]]:
    y_ego = int(event["candidates"]["local:ego"])
    y_partner = int(event["candidates"]["local:agent1"])
    late = int(event["candidates"]["edge:ego"])
    if int(event["candidates"]["edge:agent1"]) != late:
        raise ValueError(f"edge alias mismatch {event['event_id']}")
    gate = late if y_ego != y_partner else y_ego
    either = max(y_ego, y_partner)
    return {
        "local": (y_ego, y_partner),
        "late_fusion": (late, late),
        "disagreement_gate": (gate, gate),
        "OR": (either, either),
    }


def main() -> None:
    events = [json.loads(line) for line in TRACE.read_text().splitlines() if line.strip()]
    scenes = [f"{i:04d}" for i in range(9)]
    counts = {
        scene: {
            policy: {"queries": 0, "positives": 0, "negatives": 0,
                     "agent_errors": 0, "both_wrong": 0, "joint_fn": 0, "joint_fp": 0}
            for policy in POLICIES
        }
        for scene in scenes
    }
    positive_policy_mismatch = 0
    for event in events:
        scene = event["frame_id"].split("_")[1]
        truth = int(event["truth"])
        assigned = labels(event)
        if truth == 1:
            wrong = {name: int(pair[0] != truth) for name, pair in assigned.items() if name != "local"}
            local_both = int(assigned["local"][0] != truth and assigned["local"][1] != truth)
            if any(value != local_both for value in wrong.values()):
                positive_policy_mismatch += 1
        for name, pair in assigned.items():
            rec = counts[scene][name]
            rec["queries"] += 1
            rec["positives"] += int(truth == 1)
            rec["negatives"] += int(truth == 0)
            wrongs = [label != truth for label in pair]
            rec["agent_errors"] += sum(wrongs)
            both = int(all(wrongs))
            rec["both_wrong"] += both
            rec["joint_fn"] += int(truth == 1 and both)
            rec["joint_fp"] += int(truth == 0 and both)

    for scene in scenes:
        local = counts[scene]["local"]
        if local["positives"] != local["negatives"] or local["queries"] != 2 * local["positives"]:
            raise AssertionError(f"unbalanced sequence {scene}")
        if local["joint_fn"] + local["joint_fp"] != local["both_wrong"]:
            raise AssertionError(f"R2 split mismatch {scene}")
        for policy in POLICIES:
            rec = counts[scene][policy]
            if rec["queries"] != local["queries"]:
                raise AssertionError(f"unpaired queries {scene} {policy}")
            if policy != "local" and rec["agent_errors"] != 2 * rec["both_wrong"]:
                raise AssertionError(f"broadcast accounting {scene} {policy}")

    totals = {policy: {key: sum(counts[s][policy][key] for s in scenes)
                       for key in counts[scenes[0]][policy]} for policy in POLICIES}
    expected = {
        "local": {"queries": 3986, "agent_errors": 1151, "both_wrong": 105, "joint_fn": 91, "joint_fp": 14},
        "late_fusion": {"queries": 3986, "agent_errors": 388, "both_wrong": 194, "joint_fn": 91, "joint_fp": 103},
        "disagreement_gate": {"queries": 3986, "agent_errors": 384, "both_wrong": 192, "joint_fn": 91, "joint_fp": 101},
        "OR": {"queries": 3986, "agent_errors": 398, "both_wrong": 199, "joint_fn": 91, "joint_fp": 108},
    }
    for policy, checks in expected.items():
        for key, value in checks.items():
            if totals[policy][key] != value:
                raise AssertionError(f"{policy} {key}: {totals[policy][key]} != {value}")
    if positive_policy_mismatch != 0:
        raise AssertionError(f"positive queries differ across policies: {positive_policy_mismatch}")

    numerator_fields = ["sequence", "policy", "queries", "positives", "negatives",
                        "agent_labels", "agent_errors", "both_wrong", "joint_fn", "joint_fp"]
    with (OUT / "per_sequence_numerators.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=numerator_fields)
        writer.writeheader()
        for scene in scenes:
            for policy in POLICIES:
                rec = counts[scene][policy]
                writer.writerow({
                    "sequence": scene, "policy": policy,
                    "queries": rec["queries"], "positives": rec["positives"],
                    "negatives": rec["negatives"], "agent_labels": 2 * rec["queries"],
                    "agent_errors": rec["agent_errors"], "both_wrong": rec["both_wrong"],
                    "joint_fn": rec["joint_fn"], "joint_fp": rec["joint_fp"],
                })

    # Columns: queries, positives, negatives, agent_errors, both_wrong, joint_fn, joint_fp
    order = ("queries", "positives", "negatives", "agent_errors", "both_wrong", "joint_fn", "joint_fp")
    matrix = {
        policy: np.array([[counts[s][policy][key] for key in order] for s in scenes], dtype=np.float64)
        for policy in POLICIES
    }
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, len(scenes), size=(REPS, len(scenes)))

    def pooled(policy: str, sample: np.ndarray | None = None) -> dict[str, float]:
        block = matrix[policy] if sample is None else matrix[policy][sample]
        total = block.sum(axis=0)
        queries, positives, negatives, agent_errors, both_wrong, joint_fn, joint_fp = total
        return {
            "mean_error": agent_errors / (2.0 * queries),
            "r2": both_wrong / queries,
            "joint_fn": joint_fn / positives,
            "joint_fp": joint_fp / negatives,
        }

    point = {policy: pooled(policy) for policy in POLICIES}
    sampled = {policy: matrix[policy][draws].sum(axis=1) for policy in POLICIES}

    def rates_from_sums(sums: np.ndarray) -> dict[str, np.ndarray]:
        queries, positives, negatives = sums[:, 0], sums[:, 1], sums[:, 2]
        return {
            "mean_error": sums[:, 3] / (2.0 * queries),
            "r2": sums[:, 4] / queries,
            "joint_fn": sums[:, 5] / positives,
            "joint_fp": sums[:, 6] / negatives,
        }

    boot_rates = {policy: rates_from_sums(sampled[policy]) for policy in POLICIES}

    # Equal-weight mean of the nine drawn sequence rates. Secondary check only.
    def sequence_rates(policy: str) -> dict[str, np.ndarray]:
        block = matrix[policy]
        queries, positives, negatives = block[:, 0], block[:, 1], block[:, 2]
        return {
            "mean_error": block[:, 3] / (2.0 * queries),
            "r2": block[:, 4] / queries,
            "joint_fn": block[:, 5] / positives,
            "joint_fp": block[:, 6] / negatives,
        }

    seq_rates = {policy: sequence_rates(policy) for policy in POLICIES}

    rows = []
    replicate_columns = {}
    for left, right, label in CONTRASTS:
        for key, title, num_name, den_name in METRICS:
            observed = point[left][key] - point[right][key]
            replicates = boot_rates[left][key] - boot_rates[right][key]
            low, high = np.quantile(replicates, [0.025, 0.975], method="linear")
            unweighted = seq_rates[left][key][draws] - seq_rates[right][key][draws]
            unweighted_mean = unweighted.mean(axis=1)
            u_low, u_high = np.quantile(unweighted_mean, [0.025, 0.975], method="linear")
            seq_diff = seq_rates[left][key] - seq_rates[right][key]
            column = f"{left}_minus_{right}__{key}"
            replicate_columns[column] = replicates
            rows.append({
                "contrast": label,
                "left": left,
                "right": right,
                "metric": title,
                "metric_key": key,
                "estimand": "size-weighted pooled rate, sequences drawn with equal probability",
                "difference": "left minus right",
                "observed_rate_difference": observed,
                "observed_percentage_points": 100.0 * observed,
                "ci95_low": float(low),
                "ci95_high": float(high),
                "ci95_low_percentage_points": 100.0 * float(low),
                "ci95_high_percentage_points": 100.0 * float(high),
                "excludes_zero": bool(low > 0 or high < 0),
                "replicates_negative": int(np.sum(replicates < 0)),
                "replicates_zero": int(np.sum(replicates == 0)),
                "replicates_positive": int(np.sum(replicates > 0)),
                "sequences_negative": int(np.sum(seq_diff < 0)),
                "sequences_zero": int(np.sum(seq_diff == 0)),
                "sequences_positive": int(np.sum(seq_diff > 0)),
                "unweighted_mean_of_sequence_rates": float(seq_diff.mean()),
                "unweighted_ci95_low": float(u_low),
                "unweighted_ci95_high": float(u_high),
                "numerator": num_name,
                "denominator": den_name,
            })

    fieldnames = list(rows[0].keys())
    with (OUT / "paired_differences.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with (OUT / "bootstrap_replicates.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["replicate", *replicate_columns.keys()])
        writer.writeheader()
        for index in range(REPS):
            writer.writerow({
                "replicate": index,
                **{name: f"{values[index]:.12g}" for name, values in replicate_columns.items()},
            })

    method = {
        "trace": str(TRACE),
        "sequences": 9,
        "queries": 3986,
        "frames": 1993,
        "resamples": REPS,
        "seed": SEED,
        "generator": f"numpy.random.default_rng({SEED})",
        "numpy": np.__version__,
        "unit": "driving sequence",
        "draw": "9 sequences with replacement, equal probability, shared across every contrast and metric",
        "estimand": "difference of size-weighted pooled rates on the resampled multiset",
        "interval": "2.5 and 97.5 percentiles, numpy quantile method linear",
        "positive_queries_where_policies_differ": positive_policy_mismatch,
        "contrasts": [label for _, _, label in CONTRASTS],
        "direction": "first named policy minus second named policy",
    }
    (OUT / "method.json").write_text(json.dumps(method, indent=2) + "\n")
    write_report(rows, counts, scenes, totals, positive_policy_mismatch)
    print("wrote", OUT)
    for row in rows:
        print(
            f"{row['contrast']} | {row['metric']}: "
            f"{row['observed_percentage_points']:+.3f} pp "
            f"[{row['ci95_low_percentage_points']:+.3f}, {row['ci95_high_percentage_points']:+.3f}] "
            f"excludes0={row['excludes_zero']} "
            f"signs {row['replicates_negative']}/{row['replicates_zero']}/{row['replicates_positive']}"
        )


def pct(rate: float) -> str:
    return f"{100.0 * rate:.2f}"


def pp(rate: float) -> str:
    return f"{100.0 * rate:+.3f}"


def interval(row: dict) -> str:
    return f"[{pp(row['ci95_low'])}, {pp(row['ci95_high'])}] pp"


def sign_sentence(row: dict) -> str:
    negative = row["replicates_negative"]
    zero = row["replicates_zero"]
    positive = row["replicates_positive"]
    if negative == REPS:
        return "all 20,000 replicates are negative"
    if positive == REPS:
        return "all 20,000 replicates are positive"
    if zero == REPS:
        return "all 20,000 replicates are exactly zero"
    return f"{negative:,} replicates are negative, {zero:,} are zero, and {positive:,} are positive"


def write_report(rows, counts, scenes, totals, positive_mismatch: int) -> None:
    by = {(row["contrast"], row["metric_key"]): row for row in rows}
    lines: list[str] = []
    add = lines.append
    add("# Paired sequence-level uncertainty")
    add("")
    add("Nine regenerated sequences, 1,993 frames, 3,986 balanced queries. Each sequence is one cluster. A resample draws nine sequences with replacement, with equal probability, and keeps that same draw for every policy. The reported difference is the size-weighted pooled rate of the first policy minus the size-weighted pooled rate of the second. The interval is the 2.5th and 97.5th percentiles of 20,000 such differences. The generator is NumPy `default_rng(20261118)`.")
    add("")
    add("Policies use the same labels as the earlier comparison. Local keeps both detector labels. Late fusion gives both agents the recorded late-fusion label. The disagreement gate uses late fusion only when the two local labels differ, and otherwise keeps the agreed local label. OR uses 1 when either local label is 1. F0 is omitted because it changed no label.")
    add("")
    add("A negative difference means the first policy has the lower rate.")
    add("")
    add("## Pooled differences")
    add("")
    add("Denominators on the original nine sequences: mean error uses 7,972 agent labels, R2 uses 3,986 queries, and joint false negatives and false positives each use 1,993 queries. The bootstrap rebuilds those denominators from the sequences drawn in that replicate.")
    add("")
    add("| Contrast | Metric | Observed difference | 95% interval | Replicates below, at, above 0 | Sequences below, at, above 0 |")
    add("|---|---|---:|---:|---:|---:|")
    for _, _, label in CONTRASTS:
        for key, title, _, _ in METRICS:
            row = by[(label, key)]
            add(
                f"| {label} | {title} | {pp(row['observed_rate_difference'])} pp | "
                f"{interval(row)} | "
                f"{row['replicates_negative']:,} / {row['replicates_zero']:,} / {row['replicates_positive']:,} | "
                f"{row['sequences_negative']} / {row['sequences_zero']} / {row['sequences_positive']} |"
            )
    add("")
    add("## What the intervals say")
    add("")
    late_mean = by[("Late Fusion vs Local", "mean_error")]
    late_r2 = by[("Late Fusion vs Local", "r2")]
    late_fn = by[("Late Fusion vs Local", "joint_fn")]
    late_fp = by[("Late Fusion vs Local", "joint_fp")]
    gate_mean = by[("Disagreement Gate vs Local", "mean_error")]
    gate_r2 = by[("Disagreement Gate vs Local", "r2")]
    gate_fp = by[("Disagreement Gate vs Local", "joint_fp")]
    or_mean = by[("Disagreement Gate vs OR", "mean_error")]
    or_r2 = by[("Disagreement Gate vs OR", "r2")]
    or_fp = by[("Disagreement Gate vs OR", "joint_fp")]
    add(
        "Late fusion versus local moves the two error summaries in opposite directions. "
        f"Mean error changes by {pp(late_mean['observed_rate_difference'])} percentage points, "
        f"from {totals['local']['agent_errors']:,}/{2 * totals['local']['queries']:,} "
        f"to {totals['late_fusion']['agent_errors']:,}/{2 * totals['late_fusion']['queries']:,}. "
        f"The interval is {interval(late_mean)}, and {sign_sentence(late_mean)}. "
        f"R2 changes by {pp(late_r2['observed_rate_difference'])} percentage points, "
        f"from {totals['local']['both_wrong']}/{totals['local']['queries']:,} "
        f"to {totals['late_fusion']['both_wrong']}/{totals['late_fusion']['queries']:,}. "
        f"The interval is {interval(late_r2)}, and {sign_sentence(late_r2)}. "
        f"Across sequences, the R2 difference is negative in {late_r2['sequences_negative']}, "
        f"zero in {late_r2['sequences_zero']}, and positive in {late_r2['sequences_positive']}."
    )
    add("")
    add(
        "The R2 increase is joint false positives. Joint false negatives are the same count for local, late fusion, the gate, and OR: "
        f"{totals['local']['joint_fn']}/{totals['local']['positives']:,}. "
        f"Positive queries on which those policies disagree: {positive_mismatch}. "
        f"The late-fusion joint-FN interval is {interval(late_fn)}, and {sign_sentence(late_fn)}. "
        f"Joint false positives change by {pp(late_fp['observed_rate_difference'])} percentage points, "
        f"from {totals['local']['joint_fp']}/{totals['local']['negatives']:,} "
        f"to {totals['late_fusion']['joint_fp']}/{totals['late_fusion']['negatives']:,}. "
        f"The interval is {interval(late_fp)}, and {sign_sentence(late_fp)}. "
        f"The sequence signs are {late_fp['sequences_negative']} negative, "
        f"{late_fp['sequences_zero']} zero, and {late_fp['sequences_positive']} positive."
    )
    add("")
    add(
        "The disagreement gate versus local has the same pattern. "
        f"Mean error changes by {pp(gate_mean['observed_rate_difference'])} percentage points, "
        f"interval {interval(gate_mean)}, and {sign_sentence(gate_mean)}. "
        f"R2 changes by {pp(gate_r2['observed_rate_difference'])} percentage points, "
        f"from {totals['local']['both_wrong']}/{totals['local']['queries']:,} "
        f"to {totals['disagreement_gate']['both_wrong']}/{totals['disagreement_gate']['queries']:,}, "
        f"interval {interval(gate_r2)}, and {sign_sentence(gate_r2)}. "
        f"Joint false positives change by {pp(gate_fp['observed_rate_difference'])} percentage points, "
        f"from {totals['local']['joint_fp']}/{totals['local']['negatives']:,} "
        f"to {totals['disagreement_gate']['joint_fp']}/{totals['disagreement_gate']['negatives']:,}, "
        f"interval {interval(gate_fp)}, and {sign_sentence(gate_fp)}. "
        "Joint false negatives do not move."
    )
    add("")
    add(
        "The gate versus OR differs only where the two rules assign different labels. "
        f"Mean error changes by {pp(or_mean['observed_rate_difference'])} percentage points, "
        f"from {totals['OR']['agent_errors']}/{2 * totals['OR']['queries']:,} "
        f"to {totals['disagreement_gate']['agent_errors']}/{2 * totals['disagreement_gate']['queries']:,}. "
        f"The interval is {interval(or_mean)}, and {sign_sentence(or_mean)}. "
        f"R2 changes by {pp(or_r2['observed_rate_difference'])} percentage points, "
        f"from {totals['OR']['both_wrong']}/{totals['OR']['queries']:,} "
        f"to {totals['disagreement_gate']['both_wrong']}/{totals['disagreement_gate']['queries']:,}, "
        f"interval {interval(or_r2)}. "
        f"Joint false positives change by {pp(or_fp['observed_rate_difference'])} percentage points, "
        f"from {totals['OR']['joint_fp']}/{totals['OR']['negatives']:,} "
        f"to {totals['disagreement_gate']['joint_fp']}/{totals['disagreement_gate']['negatives']:,}, "
        f"interval {interval(or_fp)}. "
        f"Sequence signs for this R2 difference are {or_r2['sequences_negative']} negative, "
        f"{or_r2['sequences_zero']} zero, and {or_r2['sequences_positive']} positive. "
        "Joint false negatives do not move. "
        "For a shared-label policy, mean error equals R2, so the gate-versus-OR mean-error and R2 differences match. "
        "Their differences from local do not match, because local mean error counts every wrong agent and local R2 counts only queries where both agents are wrong."
    )
    add("")
    add("## Sequence rates")
    add("")
    add("These are the observed sequence rates. The bootstrap resamples rows of this table, not individual queries.")
    add("")
    add("| Sequence | Queries | Local mean / R2 / FN / FP | Late fusion | Gate | OR |")
    add("|---|---:|---:|---:|---:|---:|")
    for scene in scenes:
        def cell(policy: str) -> str:
            rec = counts[scene][policy]
            queries = rec["queries"]
            positives = rec["positives"]
            return (
                f"{rec['agent_errors']}/{2 * queries} = {pct(rec['agent_errors'] / (2 * queries))}% · "
                f"{rec['both_wrong']}/{queries} = {pct(rec['both_wrong'] / queries)}% · "
                f"{rec['joint_fn']}/{positives} · {rec['joint_fp']}/{positives}"
            )
        add(f"| {scene} | {counts[scene]['local']['queries']} | {cell('local')} | {cell('late_fusion')} | {cell('disagreement_gate')} | {cell('OR')} |")
    add("")
    add("The four numbers in each policy cell are mean error, R2, joint false negatives, and joint false positives. False-negative and false-positive denominators equal half the queries because every frame contributes one positive and one negative query.")
    add("")
    add("## Equal-sequence-weight check")
    add("")
    add("The primary interval weights a drawn sequence by its number of queries. A second interval gives each of the nine drawn sequences the same weight, then averages their rates. It answers a different question: the mean of sequence-level rates rather than the rate in the pooled query set. It is not a substitute for the pooled result.")
    add("")
    add("| Contrast | Metric | Unweighted mean | 95% interval |")
    add("|---|---|---:|---:|")
    for _, _, label in CONTRASTS:
        for key, title, _, _ in METRICS:
            row = by[(label, key)]
            add(
                f"| {label} | {title} | {pp(row['unweighted_mean_of_sequence_rates'])} pp | "
                f"[{pp(row['unweighted_ci95_low'])}, {pp(row['unweighted_ci95_high'])}] pp |"
            )
    add("")
    add("The signs match the pooled analysis. Magnitudes move because short sequences such as 0001, where local mean error is 24.78%, count the same as 0008, which has 750 queries and a local mean error of 2.27%.")
    add("")
    add("## Limitations")
    add("")
    late_r2 = by[("Late Fusion vs Local", "r2")]
    add(
        "There are only nine clusters. These intervals describe how the pooled difference moves when these nine recorded sequences are redrawn. They are not a population guarantee for other roads, sensors, or detectors. "
        "The published nine-sequence interval in `docs/EMPIRICAL_V2V4REAL_RESULTS.md` uses the same cluster design, 40,000 draws, and the same seed, for one contrast only: shared late-fusion joint error minus separate joint error. "
        f"That published point estimate is the R2 difference computed here, {totals['late_fusion']['both_wrong'] - totals['local']['both_wrong']}/3,986. "
        f"This run's 95% interval for that contrast is {interval(late_r2)}. "
        "The published interval is +0.872 to +3.599 percentage points. The two percentile endpoints need not match digit for digit, because this run uses 20,000 draws."
    )
    add("")
    add("Nine clusters make the bootstrap distribution coarse. There are 24,310 distinct multisets of nine sequences. A percentile interval at this size can miss the nominal 95% coverage. The draws treat sequences as independent. These nine validation sequences share one dataset, one sensor setup, and one pair of detectors, so dependence between sequences is not removed by clustering.")
    add("")
    add("Clustering does keep within-sequence dependence intact. Frames in a sequence are consecutive, and the two queries in a frame share that frame. An event-level binomial interval would treat 3,986 queries as independent and would be too narrow. The cluster interval is the appropriate one for this dependence, and it is also much less precise than the query count suggests.")
    add("")
    add("Sequences are not the same length. They range from 114 frames (228 queries) to 375 frames (750 queries). Equal-probability draws followed by pooling give a repeated long sequence more influence on the rate. The equal-weight check above is the comparison that removes that influence. Neither check creates more than nine observed clusters.")
    add("")
    add("The twelve intervals are pointwise. They are not adjusted for looking at three contrasts and four metrics together.")
    add("")
    add(f"Joint false-negative differences are exactly zero because the four policies miss the same positive queries ({positive_mismatch} positive queries differ). That is a property of these recorded labels. It is not a precise estimate of a zero effect on another dataset.")
    add("")
    add("The rates are for the balanced diagnostic task: one ground-truth-anchored positive query and one negative query per frame, radius 7.5 m, score at least 0.30. They are not V2V4Real leaderboard scores, and the policies are rules applied to recorded outputs rather than detectors run again.")
    add("")
    add("Files: `paired_differences.csv` holds the intervals, `per_sequence_numerators.csv` holds the counts, `bootstrap_replicates.csv` holds the 20,000 pooled differences, and `method.json` records the seed and percentile rule.")
    (OUT / "ANALYSIS.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
