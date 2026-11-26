#!/usr/bin/env python3
"""Figures 10 and 12, then separate deadline and packet-loss sweeps.

Uses the original three-agent frame-level F0 executor. Octopus-main is not edited.
"""
from __future__ import annotations

import csv
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path("/Users/negin/UML/Mobihoc_Extention/Octopus-main")
sys.path.insert(0, str(ROOT))

from octopus_sim.config import ExperimentConfig
from octopus_sim.simulator import run_simulation
from scripts.run_three_agent_tradeoff_frontier import (
    AGENTS,
    DEADLINES_MS,
    ROI_COUNTS,
    THRESHOLDS,
    config_for,
    evaluate_online,
    generate_arrays,
    make_fuser,
    make_trace,
)

OUT = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P1/execution_robustness")
SEED = 77109
SEEDS = (77109, 77110, 77111, 77112, 77113, 77114)
FRAMES = 600
ROIS = 2
SHOCK = 0.18
LOSS_GRID = (0.0, 0.10, 0.25, 0.50, 1.0)
LOSS_DEADLINE_MS = 150.0
METHODS = ("local", "strict", "expert")


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def execute(trace: Path, truth, pred, method: str, seed: int,
            deadline_ms: float, packet_loss: float) -> dict:
    frames, rois = truth.shape
    cfg = config_for(trace, method, frames, rois, seed)
    params = deepcopy(cfg.data)
    params["scenario"]["deadline_ms"] = deadline_ms
    params["resources"]["packet_loss"] = packet_loss
    cfg = ExperimentConfig.from_dict(params, cfg.source_path)
    addon = {} if method == "local" else {"f0_fuser": make_fuser(method)}
    out = run_simulation(cfg, detailed_events=False, **addon)
    decisions = out.fusion_decisions or []
    applied = {item["event_id"]: set(item.get("applied_agents", ())) for item in decisions}
    accepted = sum(item["action"] != "KEEP_LOCAL" for item in decisions)
    applied_agents = sum(len(item.get("applied_agents", ())) for item in decisions)
    preserved = 0
    violations = 0
    for score in out.scores:
        frame = int(score["event_id"].split(":roi_")[0].split("_")[1])
        roi = int(score["event_id"].split(":roi_")[1])
        updated = applied.get(score["event_id"], set())
        for index, agent in enumerate(AGENTS):
            if agent in updated:
                continue
            preserved += 1
            if score["predictions"][agent] != int(pred[frame, roi, index]):
                violations += 1
    queries = len(out.scores)
    labels = queries * len(AGENTS)
    wrong = sum(value is True for score in out.scores for value in score["wrong"].values())
    missing = sum(bool(value) for score in out.scores for value in score["missing"].values())
    operational = sum(score["operational_failure_count"] for score in out.scores)
    summary = out.summary
    return {
        "seed": seed,
        "method": method,
        "deadline_ms": deadline_ms,
        "packet_loss": packet_loss,
        "frames": frames,
        "queries": queries,
        "mean_error": wrong / labels,
        "r2": sum(score["error_count"] >= 2 for score in out.scores) / queries,
        "r3": sum(bool(score["all_wrong"]) for score in out.scores) / queries,
        "operational_failure": operational / labels,
        "all_three_operational_failure": sum(bool(score["all_operational_fail"]) for score in out.scores) / queries,
        "missing_labels": missing,
        "late_or_lost_agent_updates": accepted * len(AGENTS) - applied_agents,
        "accepted_queries": accepted,
        "applied_agent_updates": applied_agents,
        "detector_jobs": summary["local_inference_executions"],
        "edge_jobs": summary["edge_inference_executions"],
        "transmitted_bytes": summary["transmitted_bytes"],
        "messages_attempted": summary["messages_attempted"],
        "messages_lost": summary["messages_lost"],
        "incremental_energy_j": summary["energy_workload_incremental_j"],
        "energy_per_frame_j": summary["energy_workload_incremental_j"] / frames,
        "radio_energy_j": summary["energy_radio_incremental_j"],
        "local_labels_preserved": preserved,
        "preservation_violations": violations,
        "complete_event_rate": summary["complete_event_rate"],
    }


def roi_grid() -> list[dict]:
    truth, pred = generate_arrays(FRAMES, max(ROI_COUNTS), SEED, SHOCK)
    rows = []
    for roi in ROI_COUNTS:
        sliced_truth = truth[:, :roi].copy()
        sliced_pred = pred[:, :roi, :].copy()
        trace = make_trace(OUT / "synthetic_traces" / f"roi_{roi}.jsonl", sliced_truth, sliced_pred)
        for threshold in THRESHOLDS:
            row = evaluate_online(trace, sliced_truth, sliced_pred, "strict", SEED, threshold=threshold)
            row.update(roi_per_frame=roi, threshold=threshold, shock_probability=SHOCK)
            rows.append(row)
        print("roi grid", roi, flush=True)
    trace = make_trace(OUT / "synthetic_traces" / "roi_2_policies.jsonl", truth[:, :2].copy(), pred[:, :2, :].copy())
    for threshold in THRESHOLDS:
        row = evaluate_online(trace, truth[:, :2].copy(), pred[:, :2, :].copy(), "expert", SEED, threshold=threshold)
        row.update(roi_per_frame=2, threshold=threshold, shock_probability=SHOCK)
        rows.append(row)
    local = evaluate_online(trace, truth[:, :2].copy(), pred[:, :2, :].copy(), "local", SEED)
    local.update(roi_per_frame=2, threshold=None, shock_probability=SHOCK)
    rows.append(local)
    return rows


def plot_figures(deadline_rows: list[dict], roi_rows: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    colors = {"local": "#477C91", "majority": "#C67D36", "strict": "#4F6EB5", "expert": "#A44765", "gray": "#666D75"}
    labels = {"local": "Local", "strict": "F0 (two supporters)", "expert": "Expert override*"}
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 8.0, "axes.labelsize": 8.1,
        "xtick.labelsize": 7.4, "ytick.labelsize": 7.4, "legend.fontsize": 7.1,
        "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.6, "lines.linewidth": 1.5, "grid.alpha": 0.22,
    })
    selected = [row for row in deadline_rows if row["seed"] == SEED and row["packet_loss"] == 0.0]
    fig, axes = plt.subplots(1, 2, figsize=(4.72, 2.38), sharex=True)
    for method in METHODS:
        items = sorted([row for row in selected if row["method"] == method], key=lambda row: row["deadline_ms"])
        times = [row["deadline_ms"] for row in items]
        axes[0].plot(times, [100 * row["mean_error"] for row in items], color=colors[method], lw=1.55, label=labels[method])
        axes[1].plot(times, [1000 * row["energy_per_frame_j"] for row in items], color=colors[method], lw=1.55, label=labels[method])
    axes[0].set_ylabel("Mean agent error (%)")
    axes[0].set_ylim(0, 24)
    axes[1].set_ylabel("Modeled energy (mJ/frame)")
    axes[1].set_ylim(234, 264)
    for axis in axes:
        axis.set_xlabel("Decision deadline after frame arrival (ms)")
        axis.grid(lw=0.44)
        axis.axvline(31.5, ls=":", lw=0.9, color=colors["gray"])
    axes[0].legend(fontsize=6.7, loc="upper right", frameon=False)
    fig.subplots_adjust(left=0.12, right=0.985, top=0.97, bottom=0.22, wspace=0.33)
    fig.savefig(OUT / "fig6_deadline_cliff.pdf", bbox_inches="tight", pad_inches=0.05)
    fig.savefig(OUT / "fig6_deadline_cliff.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(4.72, 2.76), sharex=True)
    roi_colors = {1: colors["local"], 2: colors["majority"], 4: colors["strict"]}
    strict_rows = [row for row in roi_rows if row["method"] == "strict"]
    for count in ROI_COUNTS:
        items = sorted(
            [row for row in strict_rows if int(row["roi_per_frame"]) == count],
            key=lambda row: row["threshold"],
        )
        thresholds = [row["threshold"] for row in items]
        axes[0].plot(thresholds, [100 * row["share_roi_fraction"] for row in items], marker="o", ms=2.6, lw=1, ls="--", color=roi_colors[count])
        axes[0].plot(thresholds, [100 * row["actual_frame_downlink_fraction"] for row in items], marker="s", ms=2.6, lw=1.4, color=roi_colors[count])
        axes[1].plot(thresholds, [1000 * (row["energy_per_frame_j"] - 0.24) for row in items], marker="o", ms=2.6, lw=1.4, color=roi_colors[count])
    axes[0].set_ylabel("Accepted ROIs / downlink frames (%)")
    axes[0].set_ylim(-4, 107)
    axes[1].set_ylabel("Energy over local (mJ/frame)")
    axes[1].set_ylim(17.0, 18.5)
    for axis in axes:
        axis.set_xlabel("F0 acceptance threshold")
        axis.grid(lw=0.45)
        axis.set_xlim(0.79, 1.005)
    fig.legend(
        handles=[Line2D([0], [0], color=roi_colors[count], lw=1.5, label=f"{count} ROI/frame") for count in ROI_COUNTS],
        ncol=3, loc="upper center", frameon=False, fontsize=7, bbox_to_anchor=(0.53, 1.01),
    )
    axes[0].legend(
        handles=[
            Line2D([0], [0], color=colors["gray"], ls="--", marker="o", ms=3, label="Accepted ROI"),
            Line2D([0], [0], color=colors["gray"], ls="-", marker="s", ms=3, label="Frame DL"),
        ],
        fontsize=6.6, frameon=False, loc="lower left",
    )
    fig.subplots_adjust(left=0.125, right=0.985, top=0.84, bottom=0.19, wspace=0.40)
    fig.savefig(OUT / "fig5_sunk_cost_and_roi_reuse.pdf", bbox_inches="tight", pad_inches=0.05)
    fig.savefig(OUT / "fig5_sunk_cost_and_roi_reuse.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "synthetic_traces").mkdir(exist_ok=True)
    roi_rows = roi_grid()
    write_csv(OUT / "roi_threshold_physical_cost_grid.csv", roi_rows)
    robustness = []
    for seed in SEEDS:
        truth, pred = generate_arrays(FRAMES, ROIS, seed, SHOCK)
        trace = make_trace(OUT / "synthetic_traces" / f"paired_{seed}.jsonl", truth, pred)
        for deadline in DEADLINES_MS:
            for method in METHODS:
                robustness.append(execute(trace, truth, pred, method, seed, deadline, 0.0))
        for loss in LOSS_GRID:
            for method in METHODS:
                robustness.append(execute(trace, truth, pred, method, seed, LOSS_DEADLINE_MS, loss))
        print("seed", seed, flush=True)
    write_csv(OUT / "deadline_packetloss_grid.csv", robustness)
    plot_figures(robustness, roi_rows)
    violations = sum(int(row["preservation_violations"]) for row in robustness)
    provenance = {
        "figures": {"10": "fig6_deadline_cliff", "12": "fig5_sunk_cost_and_roi_reuse"},
        "source_script": "Octopus-main/scripts/run_three_agent_tradeoff_frontier.py",
        "frames": FRAMES,
        "deadline_rois": ROIS,
        "roi_counts": list(ROI_COUNTS),
        "thresholds": list(THRESHOLDS),
        "deadlines_ms": list(DEADLINES_MS),
        "packet_loss_grid": list(LOSS_GRID),
        "packet_loss_deadline_ms": LOSS_DEADLINE_MS,
        "seeds": list(SEEDS),
        "shock": SHOCK,
        "preservation_violations": violations,
        "original_sources_modified": False,
        "energy": "hypothetical E1 profile",
    }
    (OUT / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print("preservation_violations", violations)


if __name__ == "__main__":
    main()
