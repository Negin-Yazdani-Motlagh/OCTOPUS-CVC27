"""Expert-reliability grid for Section 4.3 and Figure 11.

Uses the original generator, F0 fuser, and expert-override rule. Always-A is
the broadcast of A's observed label, the baseline named in Section 4.3. It is
scored here and is not a new branch of the original fuser.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np

OCTOPUS = Path("/Users/negin/UML/Mobihoc_Extention/Octopus-main")
sys.path.insert(0, str(OCTOPUS))
from scripts.run_three_agent_tradeoff_frontier import (  # noqa: E402
    ESTIMATED_A_GRID, TRUE_A_GRID, bootstrap_pairs, evaluate_offline, generate_arrays,
)

HERE = Path(__file__).resolve().parent
SEED = 77109
FRAMES = 2000
ROIS = 2
SHOCK = 0.18
BOOTSTRAP = 2000
BOOT_SEED = SEED + 123


def always_a(truth: np.ndarray, pred: np.ndarray) -> tuple[dict, np.ndarray]:
    wrong = pred[:, :, 0] != truth
    error = np.broadcast_to(wrong[:, :, None], wrong.shape + (3,))
    summary = {
        "marginal_error": float(wrong.mean()),
        "r_ge_2": float(wrong.mean()),
        "r_all_3": float(wrong.mean()),
        "share_roi_fraction": 1.0,
    }
    cluster = np.stack((wrong.mean(axis=1),) * 3, axis=1)
    assert error.shape[-1] == 3
    return summary, cluster


def metrics(summary: dict) -> dict:
    return {
        "mean_error": summary["marginal_error"],
        "r2": summary["r_ge_2"],
        "r3": summary["r_all_3"],
        "share": summary["share_roi_fraction"],
    }


def main() -> None:
    rows = []
    caches = {}
    for true_q in TRUE_A_GRID:
        truth, pred = generate_arrays(FRAMES, ROIS, SEED, SHOCK, expert_true_error=true_q)
        local_summary, local_cluster, _, _ = evaluate_offline(truth, pred, "local")
        always_summary, always_cluster = always_a(truth, pred)
        caches[(true_q, "local")] = local_cluster
        caches[(true_q, "always_a")] = always_cluster
        for assumed_q in ESTIMATED_A_GRID:
            strict_summary, strict_cluster, _, _ = evaluate_offline(
                truth, pred, "strict", assumed_a=assumed_q)
            expert_summary, expert_cluster, _, _ = evaluate_offline(
                truth, pred, "expert", assumed_a=assumed_q)
            caches[(true_q, assumed_q, "strict")] = strict_cluster
            caches[(true_q, assumed_q, "expert")] = expert_cluster
            record = {"true_q": true_q, "assumed_q": assumed_q}
            for name, summary in (
                ("local", local_summary), ("strict", strict_summary),
                ("expert", expert_summary), ("always_a", always_summary),
            ):
                for key, value in metrics(summary).items():
                    record[f"{name}_{key}"] = value
            rows.append(record)
        print(f"true q_A={true_q:.3f}", flush=True)

    for record in rows:
        true_q, assumed_q = record["true_q"], record["assumed_q"]
        local_cluster = caches[(true_q, "local")]
        for name, cluster in (
            ("strict", caches[(true_q, assumed_q, "strict")]),
            ("expert", caches[(true_q, assumed_q, "expert")]),
            ("always_a", caches[(true_q, "always_a")]),
        ):
            delta, low, high = bootstrap_pairs(local_cluster, cluster, BOOT_SEED, BOOTSTRAP)
            for index, metric in enumerate(("r2", "r3", "mean_error")):
                record[f"{name}_minus_local_{metric}_pp"] = float(delta[index] * 100)
                record[f"{name}_minus_local_{metric}_low_pp"] = float(low[index] * 100)
                record[f"{name}_minus_local_{metric}_high_pp"] = float(high[index] * 100)

    fieldnames = list(rows[0])
    with (HERE / "calibration_grid.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    seeds = []
    for trial in range(6):
        this_seed = SEED + trial
        for true_q, assumed_q in ((0.015, 0.015), (0.45, 0.015)):
            truth, pred = generate_arrays(FRAMES, ROIS, this_seed, SHOCK, expert_true_error=true_q)
            local_summary, _, _, _ = evaluate_offline(truth, pred, "local")
            strict_summary, _, _, _ = evaluate_offline(truth, pred, "strict", assumed_a=assumed_q)
            expert_summary, _, _, _ = evaluate_offline(truth, pred, "expert", assumed_a=assumed_q)
            always_summary, _ = always_a(truth, pred)
            seeds.append({
                "seed": this_seed, "true_q": true_q, "assumed_q": assumed_q,
                "expert_minus_local_r2_pp": 100 * (expert_summary["r_ge_2"] - local_summary["r_ge_2"]),
                "expert_minus_local_r3_pp": 100 * (expert_summary["r_all_3"] - local_summary["r_all_3"]),
                "expert_minus_local_mean_pp": 100 * (expert_summary["marginal_error"] - local_summary["marginal_error"]),
                "strict_minus_local_r2_pp": 100 * (strict_summary["r_ge_2"] - local_summary["r_ge_2"]),
                "strict_minus_local_r3_pp": 100 * (strict_summary["r_all_3"] - local_summary["r_all_3"]),
                "always_a_minus_local_r2_pp": 100 * (always_summary["r_ge_2"] - local_summary["r_ge_2"]),
                "always_a_minus_local_r3_pp": 100 * (always_summary["r_all_3"] - local_summary["r_all_3"]),
            })
    with (HERE / "paired_seed_audit.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(seeds[0]))
        writer.writeheader()
        writer.writerows(seeds)

    plot(rows)
    summary = {
        "frames": FRAMES, "rois": ROIS, "queries": FRAMES * ROIS, "seed": SEED,
        "shock": SHOCK, "bootstrap": BOOTSTRAP, "bootstrap_seed": BOOT_SEED,
        "true_grid": list(TRUE_A_GRID), "assumed_grid": list(ESTIMATED_A_GRID),
        "cells": len(rows),
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


def plot(rows: list[dict]) -> None:
    trues = sorted({row["true_q"] for row in rows})
    assumed = sorted({row["assumed_q"] for row in rows})
    colors = {"local": "#477C91", "majority": "#C67D36", "strict": "#4F6EB5", "expert": "#A44765"}
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 8.0, "axes.titlesize": 8.3,
        "axes.labelsize": 8.1, "pdf.fonttype": 42, "ps.fonttype": 42,
        "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
    })
    fig, axes = plt.subplots(1, 2, figsize=(4.72, 2.60))
    image = None
    for axis, key, title in zip(
        axes, ("expert_minus_local_r2_pp", "expert_minus_local_r3_pp"),
        ("Change in R2 vs local", "Change in R3 vs local"),
    ):
        values = np.array([
            [next(row[key] for row in rows if row["true_q"] == true_q and row["assumed_q"] == assumed_q)
             for assumed_q in assumed]
            for true_q in trues
        ])
        image = axis.imshow(values, cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-22, vcenter=0, vmax=39),
                            origin="lower", aspect="auto")
        axis.set_title(title, pad=5)
        axis.set_xticks(range(len(assumed)), [f"{100 * value:g}" for value in assumed],
                        rotation=45, ha="right", fontsize=6.5)
        axis.set_yticks(range(len(trues)), [f"{100 * value:g}" for value in trues], fontsize=6.7)
        axis.set_xlabel("Assumed A error (%)")
        axis.set_ylabel("True A error (%)")
        axis.plot([assumed.index(0.015)], [trues.index(0.015)], "kx", markersize=5)
    color_axis = fig.add_axes([0.87, 0.24, 0.022, 0.61])
    bar = fig.colorbar(image, cax=color_axis)
    bar.set_label("Change (pp)", fontsize=7)
    bar.ax.tick_params(labelsize=6)
    fig.subplots_adjust(left=0.10, right=0.85, top=0.88, bottom=0.24, wspace=0.44)
    for suffix in (".pdf", ".png"):
        fig.savefig(HERE / f"fig4_expert_calibration{suffix}", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    del colors


if __name__ == "__main__":
    main()
