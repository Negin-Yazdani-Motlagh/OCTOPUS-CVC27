"""Regression checks that do not modify OCTOPUS-Sim.

Covers the 0.90 confidence boundary, decision independence from truth,
shared result IDs, and local fallback after a rejected or late update.
"""
from __future__ import annotations

import math
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path("/Users/negin/UML/Mobihoc_Extention/Octopus-main")
FINAL = Path("/Users/negin/UML/Mobihoc_Extention/Negin_validation/P1/final_validation")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(FINAL))

from octopus_fusion.contracts import AgentEvidence, FusionObservation, ReliabilityEstimate
from octopus_fusion.fusion import SelectiveFuser
from octopus_sim.config import ExperimentConfig
from octopus_sim.simulator import run_simulation
from scripts.run_three_agent_tradeoff_frontier import config_for, make_fuser, make_trace
import numpy as np

from threshold_stability import (
    LogitBoundaryFuser,
    confidence_passes_logit,
    confidence_passes_original,
    confidence_passes_tolerance,
)


def observation(predictions, groups, result_ids, *, truth_unused=None):
    evidence = tuple(
        AgentEvidence(agent, prediction, result_ids[agent], groups[agent], 20.0)
        for agent, prediction in predictions.items()
    )
    return FusionObservation("roi", "frame", 31.0, evidence, 0.5)


def reliability(agents, q=0.10):
    return ReliabilityEstimate(tuple((agent, q) for agent in agents), "test")


def test_equal_weight_margin_is_below_the_float_gate_and_on_the_logit_boundary():
    logit = math.log(0.9 / 0.1)
    confidence = 1.0 / (1.0 + math.exp(-logit))
    assert confidence < 0.90
    assert confidence_passes_original(confidence, 0.90) is False
    assert confidence_passes_logit(logit, 0.90) is True
    assert confidence_passes_tolerance(confidence, 0.90, 1e-12) is True
    # A margin one hundredth of a nat below the boundary stays rejected.
    assert confidence_passes_logit(logit - 0.01, 0.90) is False


def test_original_fuser_rejects_two_against_one_and_logit_gate_accepts_it():
    agents = ("a", "b", "c")
    predictions = {"a": 1, "b": 1, "c": 0}
    groups = {agent: agent for agent in agents}
    ids = {agent: f"result:{agent}" for agent in agents}
    obs = observation(predictions, groups, ids)
    rel = reliability(agents)
    original = SelectiveFuser().decide(obs, rel)
    revised = LogitBoundaryFuser().decide(obs, rel)
    assert original.action.value == "KEEP_LOCAL"
    assert original.fallback_reasons == ("low_surrogate_confidence",)
    assert dict(original.per_agent_decisions) == predictions
    assert revised.action.value == "SHARE_FUSED"
    assert revised.fused_prediction == 1
    assert dict(revised.per_agent_decisions) == {agent: 1 for agent in agents}


def test_truth_is_not_an_input_and_flipping_it_does_not_change_the_decision(tmp_path):
    truth = np.array([[1, 0]], dtype=np.int8)
    pred = np.array([[[1, 0, 1], [0, 0, 1]]], dtype=np.int8)
    trace = make_trace(tmp_path / "trace.jsonl", truth, pred)
    flipped = make_trace(tmp_path / "flipped.jsonl", 1 - truth, pred)
    cfg = config_for(trace, "strict", 1, 2, 5701)
    other = config_for(flipped, "strict", 1, 2, 5701)
    first = run_simulation(cfg, detailed_events=False, f0_fuser=make_fuser("strict"))
    second = run_simulation(other, detailed_events=False, f0_fuser=make_fuser("strict"))
    assert [item["action"] for item in first.fusion_decisions] == [item["action"] for item in second.fusion_decisions]
    assert [item["fused_prediction"] for item in first.fusion_decisions] == [
        item["fused_prediction"] for item in second.fusion_decisions
    ]
    assert [score["ground_truth"] for score in first.scores] != [score["ground_truth"] for score in second.scores]


def test_shared_result_id_must_keep_one_group_and_one_prediction():
    predictions = {"a": 1, "b": 1, "c": 1}
    ids = {"a": "shared", "b": "shared", "c": "shared"}
    try:
        observation(predictions, {agent: agent for agent in predictions}, ids)
    except ValueError as exc:
        assert "independent dependence groups" in str(exc)
    else:
        raise AssertionError("distinct groups were accepted for one result ID")
    conflict = dict(predictions)
    conflict["c"] = 0
    try:
        observation(conflict, {agent: "shared" for agent in predictions}, ids)
    except ValueError as exc:
        assert "contradict itself" in str(exc)
    else:
        raise AssertionError("one result ID carried two predictions")
    legal = observation(predictions, {agent: "shared" for agent in predictions}, ids)
    separate = observation(
        predictions, {agent: "shared" for agent in predictions},
        {agent: f"result:{agent}" for agent in predictions},
    )
    rel = reliability(predictions)
    assert SelectiveFuser().decide(legal, rel) == SelectiveFuser().decide(separate, rel)


def test_rejected_and_late_updates_keep_the_local_prediction(tmp_path):
    truth = np.array([[1, 0]], dtype=np.int8)
    pred = np.array([[[1, 1, 0], [0, 1, 0]]], dtype=np.int8)
    trace = make_trace(tmp_path / "trace.jsonl", truth, pred)
    cfg = config_for(trace, "strict", 1, 2, 5701)
    params = deepcopy(cfg.data)
    params["scenario"]["deadline_ms"] = 21
    short = ExperimentConfig.from_dict(params, cfg.source_path)
    late = run_simulation(short, detailed_events=False, f0_fuser=make_fuser("strict"))
    assert late.summary["edge_inference_executions"] == 1
    assert late.summary["local_inference_executions"] == 3
    assert late.summary["complete_event_rate"] == 1
    for score, roi in zip(late.scores, (0, 1)):
        for index, agent in enumerate(("a", "b", "c")):
            assert score["predictions"][agent] == int(pred[0, roi, index])
            assert score["missing"][agent] is False
    assert late.summary["energy_workload_incremental_j"] > 0
    assert late.summary["energy_baseline_j"] > 0
    assert math.isclose(
        late.summary["energy_total_j"],
        late.summary["energy_baseline_j"] + late.summary["energy_workload_incremental_j"],
        rel_tol=0.0, abs_tol=1e-9,
    )
