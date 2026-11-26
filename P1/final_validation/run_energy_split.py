#!/usr/bin/env python3
"""Record idle baseline and incremental energy for the synthetic deadline and loss grid.

Reuses the original three-agent executor and the same seeds as
P1/execution_robustness. Previous CSVs are not rewritten.
"""
from __future__ import annotations

import csv
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path("/Users/negin/UML/Mobihoc_Extention/Octopus-main")
EXEC = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P1/execution_robustness")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(EXEC))

from octopus_sim.config import ExperimentConfig
from octopus_sim.simulator import run_simulation
from scripts.run_three_agent_tradeoff_frontier import DEADLINES_MS, config_for, generate_arrays, make_fuser, make_trace
import run_execution_robustness as prior

OUT = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P1/final_validation")


def run_case(trace, truth, method, seed, deadline_ms, packet_loss):
    frames, _rois = truth.shape
    cfg = config_for(trace, method, frames, truth.shape[1], seed)
    params = deepcopy(cfg.data)
    params["scenario"]["deadline_ms"] = deadline_ms
    params["resources"]["packet_loss"] = packet_loss
    cfg = ExperimentConfig.from_dict(params, cfg.source_path)
    addon = {} if method == "local" else {"f0_fuser": make_fuser(method)}
    summary = run_simulation(cfg, detailed_events=False, **addon).summary
    return {
        "seed": seed,
        "method": method,
        "deadline_ms": deadline_ms,
        "packet_loss": packet_loss,
        "frames": frames,
        "energy_baseline_j": summary["energy_baseline_j"],
        "energy_incremental_j": summary["energy_workload_incremental_j"],
        "energy_post_window_incremental_j": summary["energy_post_window_incremental_j"],
        "energy_total_j": summary["energy_total_j"],
        "energy_window_ms": summary["energy_measurement_window_ms"],
        "complete_event_rate": summary["complete_event_rate"],
        "detector_jobs": summary["local_inference_executions"],
        "edge_jobs": summary["edge_inference_executions"],
        "transmitted_bytes": summary["transmitted_bytes"],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in prior.SEEDS:
        truth, pred = generate_arrays(prior.FRAMES, prior.ROIS, seed, prior.SHOCK)
        trace = make_trace(OUT / "traces" / f"paired_{seed}.jsonl", truth, pred)
        for deadline in DEADLINES_MS:
            for method in prior.METHODS:
                rows.append(run_case(trace, truth, method, seed, deadline, 0.0))
        for loss in prior.LOSS_GRID:
            for method in prior.METHODS:
                rows.append(run_case(trace, truth, method, seed, prior.LOSS_DEADLINE_MS, loss))
        print("energy seed", seed, flush=True)
    with (OUT / "deadline_loss_energy_split.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
