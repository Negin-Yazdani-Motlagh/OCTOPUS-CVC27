#!/usr/bin/env python3
"""Compare the original confidence gate with a logit-boundary gate.

The original test rejects when ``confidence < 0.90`` after converting the
score with a sigmoid. A one-weight margin at error 0.10 has logit ``log(9)``
and floating-point confidence ``0.8999999999999999``, so that gate rejects it.

This script leaves the installed fuser unchanged. Its alternate gate rejects
low confidence only when ``abs(logit) < log(t / (1 - t))``. A probability
tolerance of ``1e-12`` accepts the same boundary value.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path("/Users/negin/UML/Mobihoc_Extention/Octopus-main")
REMAINING = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P1/remaining_mechanisms")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REMAINING))

import numpy as np
from octopus_fusion.contracts import Action, AgentEvidence, FusionDecision, FusionObservation, ReliabilityEstimate
from octopus_fusion.fusion import SelectiveFuser
import run_remaining as base

OUT = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P1/final_validation")
TOLERANCE = 1e-12


def logit_boundary(threshold: float) -> float:
    return math.log(threshold / (1.0 - threshold))


def confidence_passes_original(confidence: float, threshold: float) -> bool:
    return not confidence < threshold


def confidence_passes_logit(logit: float, threshold: float, tolerance: float = TOLERANCE) -> bool:
    """Accept the exact mathematical boundary despite a one-ulp weight deficit.

    ``log1p(-q) - log(q)`` at q=0.10 is ``4.44e-16`` below ``log(9)``. A strict
    comparison with the boundary repeats the rejection. The documented absolute
    tolerance is ``1e-12`` nats, far below a real change in the error rate and
    large enough to cover that rounding gap.
    """
    return abs(logit) + tolerance >= logit_boundary(threshold)


def confidence_passes_tolerance(confidence: float, threshold: float, tolerance: float = TOLERANCE) -> bool:
    return confidence + tolerance >= threshold


class LogitBoundaryFuser:
    """Call the original fuser, then drop only a boundary confidence rejection."""

    def __init__(self) -> None:
        self.inner = SelectiveFuser(base.F0)

    def decide(self, observation, reliability, *, risk_bounds=None):
        decision = self.inner.decide(observation, reliability, risk_bounds=risk_bounds)
        if "low_surrogate_confidence" not in decision.fallback_reasons:
            return decision
        if not confidence_passes_logit(decision.surrogate_score, self.inner.config.min_score_confidence):
            return decision
        reasons = tuple(reason for reason in decision.fallback_reasons if reason != "low_surrogate_confidence")
        if reasons:
            return decision
        label = 1 if decision.surrogate_score > 0 else 0
        action = Action.MASK_AND_FUSE if decision.masked_agents else Action.SHARE_FUSED
        return FusionDecision(
            decision.event_id, decision.frame_id, action,
            tuple((agent, label) for agent, _ in decision.per_agent_decisions),
            label, decision.surrogate_score, decision.score_confidence,
            decision.used_groups, decision.supporting_groups, decision.masked_agents,
            (), decision.estimator_id,
        )


def boundary_case() -> dict:
    logit = math.log(0.9 / 0.1)
    confidence = 1.0 / (1.0 + math.exp(-logit))
    threshold = 0.90
    return {
        "logit": logit,
        "confidence": confidence,
        "threshold": threshold,
        "logit_boundary": logit_boundary(threshold),
        "original_accepts": confidence_passes_original(confidence, threshold),
        "logit_accepts": confidence_passes_logit(logit, threshold),
        "tolerance_1e_12_accepts": confidence_passes_tolerance(confidence, threshold),
        "documented_tolerance": TOLERANCE,
    }


def apply_gate(agents, local, ids, event_id, frame_id, gate: str):
    if gate == "majority":
        chosen, _, _ = base.final_predictions(
            agents, local, "majority", {agent: agent for agent in agents}, ids,
            {agent: base.Q_EQUAL for agent in agents}, event_id, frame_id,
        )
        return chosen
    evidence = tuple(AgentEvidence(agent, local[agent], ids[agent], agent, 20.0) for agent in agents)
    observation = FusionObservation(event_id, frame_id, 31.0, evidence, 0.5)
    reliability = ReliabilityEstimate(tuple((agent, base.Q_EQUAL) for agent in agents), "configured_q")
    fuser = SelectiveFuser(base.F0) if gate == "original_float" else LogitBoundaryFuser()
    return dict(fuser.decide(observation, reliability).per_agent_decisions)


def score(truth, pred, agents, gate: str) -> np.ndarray:
    wrong = np.empty(pred.shape, dtype=bool)
    for frame in range(pred.shape[0]):
        ids = {agent: f"S{frame:05d}:result:{agent}" for agent in agents}
        for roi in range(pred.shape[1]):
            local = {agent: int(pred[frame, roi, index]) for index, agent in enumerate(agents)}
            chosen = apply_gate(agents, local, ids, f"S{frame:05d}:r{roi}", f"S{frame:05d}", gate)
            for index, agent in enumerate(agents):
                wrong[frame, roi, index] = chosen[agent] != int(truth[frame, roi])
    return wrong


def rates(wrong: np.ndarray) -> dict[str, int | float]:
    count = wrong.sum(axis=2)
    queries = wrong.shape[0] * wrong.shape[1]
    result = {
        "wrong_labels": int(wrong.sum()),
        "labels": int(queries * wrong.shape[2]),
        "queries": int(queries),
        "mean_error": float(wrong.mean()),
    }
    for m in range(2, wrong.shape[2] + 1):
        result[f"r{m}_count"] = int((count >= m).sum())
        result[f"r{m}"] = float((count >= m).mean())
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    case = boundary_case()
    (OUT / "threshold_boundary.json").write_text(json.dumps(case, indent=2) + "\n", encoding="utf-8")
    rows = []
    for seed in base.SEEDS:
        for study, agents in (("three", base.THREE), ("five", base.FIVE)):
            rng = np.random.default_rng(seed)
            truth = rng.integers(0, 2, size=(base.FRAMES, base.ROIS), dtype=np.int8)
            pred = np.bitwise_xor(truth[:, :, None], rng.random((base.FRAMES, base.ROIS, len(agents))) < base.Q_EQUAL)
            scored = {gate: score(truth, pred, agents, gate) for gate in ("original_float", "logit_boundary", "majority")}
            for gate, wrong in scored.items():
                row = {"seed": seed, "study": study, "gate": gate, **rates(wrong)}
                row["labels_match_majority"] = int(np.array_equal(wrong, scored["majority"]))
                row["labels_match_original"] = int(np.array_equal(wrong, scored["original_float"]))
                rows.append(row)
        print("threshold seed", seed, flush=True)
    fields = list(rows[0])
    for row in rows[1:]:
        for key in row:
            if key not in fields:
                fields.append(key)
    with (OUT / "threshold_comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, restval="")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(case))


if __name__ == "__main__":
    main()
