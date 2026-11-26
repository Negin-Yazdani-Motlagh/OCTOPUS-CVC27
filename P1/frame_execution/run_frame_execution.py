#!/usr/bin/env python3
"""Section 5 / Figure 9 on the regenerated sequence 0007 trace.

Uses the original E1 evaluator. The copied scenario points at an extracted
0007 trace; Octopus-main sources and configs are not edited.
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
from scripts.run_e1_multiobjective import (
    POLICIES,
    evaluate_dataset,
    make_variants,
    temporal_block_sensitivity,
)

OUT = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P1/frame_execution")
FULL_TRACE = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P0/v2v4real_all/trace.jsonl")
BOOTSTRAP = 3000
BLOCK = 12
BOOT_SEED = 711910


def extract_0007() -> tuple[Path, int, int]:
    lines = []
    slots = []
    for line in FULL_TRACE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if str(row["frame_id"]).startswith("v2v4real_0007_"):
            lines.append(row)
            slots.append(row["arrival_slot"])
    if not lines:
        raise SystemExit("sequence 0007 not found in regenerated trace")
    origin = min(slots)
    frames = []
    for row in lines:
        row["arrival_slot"] = row["arrival_slot"] - origin
        frames.append(row["frame_id"])
    unique = list(dict.fromkeys(frames))
    if len(lines) != 442 or len(unique) != 221:
        raise SystemExit(f"unexpected 0007 size: {len(unique)} frames, {len(lines)} queries")
    if max(row["arrival_slot"] for row in lines) != 220:
        raise SystemExit("0007 arrival slots are not 221 consecutive frames")
    path = OUT / "seq0007_trace.jsonl"
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in lines), encoding="utf-8")
    return path, len(unique), len(lines)


def load_config(trace: Path, granularity: str) -> ExperimentConfig:
    raw = json.loads((ROOT / "examples/energy/v2v4real_0007_energy.json").read_text(encoding="utf-8"))
    raw["world"]["trace_file"] = str(trace)
    raw["world"]["execution_granularity"] = granularity
    raw["scenario"]["episodes"] = 442
    dest = OUT / f"scenario_{granularity}.json"
    dest.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return ExperimentConfig.load(dest)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def physical_accounting(conf: ExperimentConfig, granularity: str) -> list[dict]:
    rows = []
    for prob, variant in make_variants(conf):
        outcome = run_simulation(variant, detailed_events=False)
        summ = outcome.summary
        rows.append({
            "execution_granularity": granularity,
            "fusion_target_probability": prob,
            "decision_events": summ["episodes"],
            "physical_execution_batches": summ["physical_execution_batches"],
            "frame_projection_cache_hits": summ["frame_projection_cache_hits"],
            "decision_events_sharing_physical_frame": summ["decision_events_sharing_physical_frame"],
            "local_jobs": summ["local_inference_executions"],
            "edge_jobs": summ["edge_inference_executions"],
            "bytes_transmitted": summ["transmitted_bytes"],
            "compute_executions_by_model": json.dumps(summ["compute_executions_by_model"], sort_keys=True),
            "marginal_error_rate": summ["marginal_error_rate_all_events"],
            "joint_error_rate": summ["joint_all_error_rate"],
            "joint_error_count": summ["joint_all_error_count"],
            "energy_incremental_total_j": summ["energy_workload_incremental_j"],
            "energy_j_per_decision": summ["energy_workload_incremental_j"] / summ["episodes"],
            "energy_j_per_frame": summ["energy_workload_incremental_j"] / summ["physical_execution_batches"],
            "actual_shared_event_rate": summ["events_with_shared_inference_rate"],
        })
    return rows


def plot_figure9(rows: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    selected = sorted(
        [row for row in rows if row["dataset"] == "v2v4real_0007"],
        key=lambda row: float(row["fusion_target_probability"]),
    )
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 8.5, "axes.titlesize": 9,
        "axes.labelsize": 8.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.6, "grid.alpha": 0.23, "lines.linewidth": 1.5,
    })
    colors = {"marginal_error": "#41778A", "joint_error": "#AA4966"}
    fig, axes = plt.subplots(1, 2, figsize=(4.72, 2.42))
    for ax, key, title, color in zip(
        axes, ["marginal_error", "joint_error"], ["Mean agent error", "Both wrong"],
        [colors["marginal_error"], colors["joint_error"]],
    ):
        y = np.array([100 * float(row[key + "_rate"]) for row in selected])
        lo = np.array([100 * float(row[key + "_ci_low"]) for row in selected])
        hi = np.array([100 * float(row[key + "_ci_high"]) for row in selected])
        energy = np.array([2 * float(row["energy_incremental_per_decision_j"]) for row in selected])
        elo = np.array([2 * float(row["energy_sensitivity_min_per_decision_j"]) for row in selected])
        ehi = np.array([2 * float(row["energy_sensitivity_max_per_decision_j"]) for row in selected])
        ax.errorbar(
            energy, y, yerr=[y - lo, hi - y], xerr=[energy - elo, ehi - energy],
            color=color, marker="o", ms=3.5, lw=1.1, capsize=2,
        )
        for x, value, row in zip(energy, y, selected):
            ax.annotate(
                f"{100 * float(row['fusion_target_probability']):g}%",
                (x, value), xytext=(3, 4), textcoords="offset points", fontsize=6.6,
            )
        ax.set_title(title)
        ax.set_xlabel("Modeled energy (J/frame)")
        ax.set_ylabel("Error (%)")
        ax.grid(lw=0.4)
        ax.set_xlim(0.145, 0.365)
        ax.set_ylim(bottom=0)
    fig.tight_layout(pad=0.55, w_pad=1.2)
    fig.savefig(OUT / "fig_real_energy_tradeoff.pdf", bbox_inches="tight", pad_inches=0.06)
    fig.savefig(OUT / "fig_real_energy_tradeoff.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    trace, frames, queries = extract_0007()
    frame_conf = load_config(trace, "frame")
    decision_conf = load_config(trace, "decision")
    rows, sensitivity = evaluate_dataset(frame_conf, "v2v4real_0007", BOOTSTRAP, BLOCK, BOOT_SEED)
    write_csv(OUT / "multiobjective_policy_metrics.csv", rows)
    write_csv(OUT / "energy_profile_sensitivity_grid.csv", sensitivity)
    blocks = temporal_block_sensitivity(frame_conf, BOOTSTRAP, BOOT_SEED)
    write_csv(OUT / "v2v4real_block_bootstrap_sensitivity.csv", blocks)
    accounting = physical_accounting(frame_conf, "frame") + physical_accounting(decision_conf, "decision")
    write_csv(OUT / "physical_vs_query_accounting.csv", accounting)
    plot_figure9(rows)
    provenance = {
        "experiment": "Section 5 RQ3 Figure 9, original E1 frame-randomized cooperation",
        "source_script": "Octopus-main/scripts/run_e1_multiobjective.py",
        "source_config": "Octopus-main/examples/energy/v2v4real_0007_energy.json",
        "trace": str(trace),
        "trace_parent": str(FULL_TRACE),
        "frames": frames,
        "queries": queries,
        "arrival_slots": "subtracted the regenerated nine-sequence offset; 0007 frames remain consecutive",
        "policies": list(POLICIES),
        "seed": 20261118,
        "bootstrap": {"iterations": BOOTSTRAP, "block_length_frames": BLOCK, "seed": BOOT_SEED},
        "energy": "hypothetical E1 profile; horizontal range is nine radio/fusion multipliers, not a confidence interval",
        "original_sources_modified": False,
    }
    (OUT / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        print(
            f"k={float(row['fusion_target_probability']):.2f} "
            f"mean={100 * float(row['marginal_error_rate']):.3f} "
            f"R2={100 * float(row['joint_error_rate']):.3f} "
            f"E/dec={float(row['energy_incremental_per_decision_j']):.6f} "
            f"jobs={row['local_jobs']}/{row['edge_jobs']} bytes={row['bytes_transmitted']}"
        )


if __name__ == "__main__":
    main()
