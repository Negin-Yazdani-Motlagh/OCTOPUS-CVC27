#!/usr/bin/env python3
"""Synthetic half of the original 3,000-event E1 multiobjective experiment.

The published runner also replays sequence 0007. That half is already in
P1/frame_execution. This script calls the same evaluate_dataset function on
the synthetic configuration only.
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path("/Users/negin/UML/Mobihoc_Extention/Octopus-main")
sys.path.insert(0, str(ROOT))

from octopus_sim.config import ExperimentConfig
from scripts.run_e1_multiobjective import _write_csv, evaluate_dataset

OUT = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P1/final_validation")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    synth = ExperimentConfig.load(ROOT / "examples/energy/three_agent_per_bit.json")
    raw = deepcopy(synth.data)
    raw["scenario"]["episodes"] = 3000
    synth = ExperimentConfig.from_dict(raw, synth.source_path)
    rows, sensitivity = evaluate_dataset(synth, "three_agent_synthetic", 3000, 1, 711911)
    _write_csv(OUT / "synthetic_e1_3000.csv", rows)
    _write_csv(OUT / "synthetic_e1_energy_sensitivity.csv", sensitivity)
    for row in rows:
        print(
            f"k={row['fusion_target_probability']:.2f} "
            f"joint={100 * row['joint_error_rate']:.3f} "
            f"mean={100 * row['marginal_error_rate']:.3f} "
            f"E/event={row['energy_incremental_per_decision_j']:.4f} "
            f"baseline={row['energy_baseline_total_j']:.4f} "
            f"latency={row['latency_mean_ms']:.3f}"
        )


if __name__ == "__main__":
    main()
