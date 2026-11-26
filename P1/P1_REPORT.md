# P1 report: controlled mechanisms and physical execution

This report covers the P1 acceptance items in Section 6 of `Octopus-main/docs/RESEARCH_GUIDE.md`. The runs use OCTOPUS-Sim 0.7.1 and the original scripts. No original source file, configuration, or manuscript page was edited. Energy figures are hypothetical E1 profiles, not hardware measurements. Truth is used only for scoring.

The experiments are in `P1/three_agent/`, `P1/five_agent/`, `P1/reliability_robustness/`, `P1/frame_execution/`, `P1/execution_robustness/`, `P1/remaining_mechanisms/`, and `P1/final_validation/`. The equal-error partition check was completed earlier and is stored in `reuse_toy.csv`, not under `P1/`.

## Reproduced manuscript results

### Analytical partitions

`examples/reuse_toy.py` at q = 0.10 matches the guide. Five receivers and three jobs give R3 = 2.8% for groups 2+2+1 and R3 = 10% for groups 3+1+1. Both give R5 = 0.1%. Mean error stays at q. The formula is the product over groups of `(1-q) + q z^(s_j)`.

### Table 3 and Figure 7

`Octopus-main/scripts/run_three_agent_tradeoff_frontier.py` was run with 2,000 frames, 2 queries per frame, 600 online frames, seed `77109`, and 2,000 bootstrap replicates. A has true error 0.015. B and C have 0.26 and 0.32, with a shared shock. Table 3 is shock 0.18, on 4,000 queries and 12,000 labels.

| Policy | Mean error | R2 | R3 |
|---|---:|---:|---:|
| Local | 2,403/12,000 = 20.025% | 792/4,000 = 19.800% | 8/4,000 = 0.200% |
| Majority broadcast | 2,376/12,000 = 19.800% | 792/4,000 = 19.800% | 792/4,000 = 19.800% |
| Conservative F0 | 1,639/12,000 = 13.658% | 792/4,000 = 19.800% | 16/4,000 = 0.400% |
| Expert override | 165/12,000 = 1.375% | 55/4,000 = 1.375% | 55/4,000 = 1.375% |

The manuscript’s 20.03%, 13.66%, and 1.38% are these rates rounded. Conservative F0 lowers mean error by 6.367 points and leaves R2 unchanged. Its paired frame-bootstrap intervals, seed `77109+123`, are mean error [−6.775, −5.950] and R3 [+0.075, +0.350], both versus local. The expert-minus-local intervals are R2 [−19.651, −17.150] and R3 [+0.875, +1.525]. The manuscript prints [−19.65, −17.15] and [+0.88, +1.53].

On this seed the override copies A on all 4,000 queries. It is the always-A baseline. Figure 7 is `P1/three_agent/fig3_three_agent_risk_tradeoff.pdf`. At every shock in {0, 0.06, 0.12, 0.18, 0.24}, local, majority, and conservative F0 share one R2 curve, and majority’s R3 equals that R2.

### Figure 8

`Octopus-main/scripts/run_f0_cvc_parameter_study.py` was run with 2,000 frames, 2 queries, seed `5701`, 2,500 bootstrap replicates, and `--skip-v2v`. Agents a and b are independent at 0.055 and 0.080. Agents c, d, and e have error 0.18 and share one error draw with probability ρ. The group labels are supplied, not estimated. At ρ = 0.75, on 4,000 queries and 20,000 labels:

| Policy | Mean error | R3 | R5 |
|---|---:|---:|---:|
| Local | 2,743/20,000 = 13.715% | 581/4,000 = 14.525% | 2/4,000 = 0.050% |
| Weighted broadcast | 495/20,000 = 2.475% | 99/4,000 = 2.475% | 99/4,000 = 2.475% |
| Correctly grouped F0 | 854/20,000 = 4.270% | 99/4,000 = 2.475% | 11/4,000 = 0.275% |
| Incorrectly grouped F0 | 2,011/20,000 = 10.055% | 581/4,000 = 14.525% | 80/4,000 = 2.000% |

Grouped-minus-local is −12.050 points in R3, interval [−13.075, −11.050], and +0.225 points in R5, interval [+0.100, +0.400]. The manuscript’s 14.53/0.05, 2.48/0.28, 14.53/2.00, 2.48/2.48, [−13.08, −11.05], and [+0.10, +0.40] are these values rounded. Figure 8 is `P1/five_agent/fig_five_agent_lineage.pdf`. Grouped R3 equals weighted R3 at every ρ in {0, 0.25, 0.50, 0.75, 1}. Ungrouped R3 equals local R3 at every ρ. Local R5 is an observed zero at ρ = 0 and 0.25.

### Figure 11

`P1/reliability_robustness/run_reliability.py` reuses the original grids and the same latent uniforms. True error of A is {0.015, 0.05, 0.10, 0.20, 0.30, 0.40, 0.45}. Assumed error is {0.003, 0.006, 0.010, 0.015, 0.020, 0.030, 0.045, 0.060, 0.100}. Shock stays at 0.18. Seed `77109`. There are 63 cells.

At true and assumed error 1.5%, the override equals always-A: 165/12,000 = 1.375% on mean error, R2, and R3. Versus local, R2 changes by −18.425 points, interval [−19.651, −17.150], and R3 by +1.175 points, interval [+0.875, +1.525]. At true error 45% and assumed error 1.5%, the same broadcast gives 5,430/12,000 = 45.250%. R2 rises by 16.750 points, interval [+14.900, +18.675], and R3 by 36.800 points, interval [+35.325, +38.325]. The manuscript states 16.75 and 36.80. The figure is `P1/reliability_robustness/fig4_expert_calibration.pdf`.

The override fires only when the declared error is 0.3%, 0.6%, 1.0%, or 1.5%. At a declared error of 2% or higher it matches conservative F0. Conservative F0’s R2 difference from local is 0 on all 63 cells.

### Figure 9

`P1/frame_execution/run_frame_execution.py` calls `Octopus-main/scripts/run_e1_multiobjective.py` on sequence 0007 extracted from `P0/v2v4real_all/trace.jsonl`. The copied scenario is `P1/frame_execution/scenario_frame.json`, based on `Octopus-main/examples/energy/v2v4real_0007_energy.json`. Seed `20261118`. There are 221 frames and 442 queries. Cooperation is chosen once per frame.

| Target | Frames fused | Mean error | R2 | Energy (J/frame) | Detector runs | Edge jobs | Bytes |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0% | 0/221 | 200/884 = 22.624% | 4/442 = 0.905% | 0.160 | 442 | 0 | 0 |
| 25% | 52/221 | 154/884 = 17.421% | 4/442 = 0.905% | 0.180 | 442 | 52 | 439,296 |
| 50% | 107/221 | 111/884 = 12.557% | 6/442 = 1.357% | 0.200 | 442 | 107 | 903,936 |
| 75% | 162/221 | 72/884 = 8.145% | 10/442 = 2.262% | 0.221 | 442 | 162 | 1,368,576 |
| 100% | 221/221 | 32/884 = 3.620% | 16/442 = 3.620% | 0.243 | 442 | 221 | 1,867,008 |

The manuscript’s endpoints, 22.62% to 3.62%, 0.90% to 3.62%, and 0.160 to 0.243 J/frame, match. At 25% the joint-error count stays at 4 and mean error is 17.42%. The 12-frame moving-block intervals, 3,000 replicates, seed `711910`, are in `P1/frame_execution/multiobjective_policy_metrics.csv`. The figure is `P1/frame_execution/fig_real_energy_tradeoff.pdf`. Idle baseline energy is 2,230.08 J on every row. Incremental energy is reported separately.

### Figures 10 and 12

`P1/execution_robustness/run_execution_robustness.py` uses the original 600-frame executor, seed `77109`, and shock 0.18. Local detection finishes at 20 ms. The fused update arrives at 31.5 ms.

At 21 ms, local, conservative F0, and the expert override all score 731/3,600 = 20.306%, R2 246/1,200 = 20.500%, and R3 4/1,200 = 0.333%. F0 has accepted 950 queries and the override has accepted all 1,200, but every accepted update is late. At 32 ms the same jobs, bytes, and energy are charged, and the updates apply. Conservative F0 falls to 508/3,600 = 14.111% with R2 unchanged. The override falls to 48/3,600 = 1.333%. The manuscript’s 20.31%, 14.11%, and 1.33% are these rates. Figure 10 is `P1/execution_robustness/fig6_deadline_cliff.pdf`.

Figure 12 is the nested 1-, 2-, and 4-query threshold grid, `fig5_sunk_cost_and_roi_reuse.pdf`. At two queries and threshold 0.90, F0 accepts 956/1,200 queries and transmits a frame result on 574/600 frames. At four queries, 79.38% acceptance produces a downlink on all 600 frames. Threshold 0.999 accepts nothing, yet energy remains 0.25736 J/frame because 1,800 detector runs, 600 edge decisions, and 3,686,400 upload bytes have already been spent. Local energy is 0.24000 J/frame.

## Additional findings

Trusting A is already costly for all-three error when A is reliable. At true error 1.5% and a declared error of 1.5%, R3 rises by 1.175 points. Mean error and R2 become worse once the true error reaches 30% while the declared error stays at or below 1.5%. On this draw the increases at 30% are 0.667, 5.100, and 24.425 points for mean error, R2, and R3.

Sequence 0007 charged once per frame uses 221 execution batches. Charging once per query uses 442 batches and doubles the endpoint work: 884 detector runs, 442 edge jobs, 3,734,016 bytes, and 70.720 J and 107.586 J of incremental energy. The 0% and 100% error counts do not change. The 25% per-query coin does change the errors, to 161/884 = 18.213% and 6 joint errors, because the coin is no longer one draw per frame. The frame-level coin is the one that matches Section 5.

Packet loss, with the deadline held at 150 ms, does not erase a local label. At 100% loss both fusion policies return the local error and run no edge job, but they still attempt 1,800 uploads, transmit 3,686,400 bytes, and spend 0.24836 J/frame. At 10% loss on seed `77109`, conservative F0 mean error rises from 14.111% to 589/3,600 = 16.361%, and the override rises from 1.333% to 283/3,600 = 7.861%.

The first 180 five-agent frames were executed in the simulator. Offline labels matched the executed predictions on 14 checked fields per policy (`P1/five_agent/online_executor_consistency.csv`).

## Baselines that are as good as F0 on some objective

These are reported because a simpler rule wins part of the comparison.

- Always-A equals the expert override on every cell where the override fires, including the favorable Table 3 cell. The override is not a third accuracy regime there.
- Majority broadcast matches conservative F0 on R2 and is much worse on R3: 19.800% versus 0.400% at shock 0.18. Its mean error, 19.800%, is only 0.225 points below local.
- Weighted broadcast matches grouped F0 on R3 at every ρ and has lower mean error, 2.475% versus 4.270% at ρ = 0.75. It also has higher R5, 2.475% versus 0.275%, because it has no fallback. The mean-error advantage is the corrections grouped F0 declines.
- Incorrect grouping leaves R3 equal to local and raises R5. Counting the clique as three independent reports does not improve the majority-failure rate.
- On sequence 0007, raising the cooperation probability lowers mean error and raises R2. Local-only is better on joint error and on energy. Full late fusion is better on mean error. Neither dominates both objectives.

## Robustness and uncertainty

| Check | Design | Result |
|---|---|---|
| Three-agent seeds `77109`–`77114` | Same shock 0.18, paired policies | Expert-minus-local R2 stays in [−20.25, −17.45] points and R3 in [+1.000, +1.425] |
| Calibration seeds, assumed error 1.5% | True error 1.5% and 45% | Signs unchanged. At 45%, R2 changes lie in [+13.700, +18.025] and R3 in [+33.925, +37.000] |
| Five-agent ρ sweep | Seeds `5701`–`5706`, shared latent draws within each seed | Grouped R3 equals weighted R3 at all five weights. Ungrouped R3 equals local R3. Ranges are in `P1/remaining_mechanisms/` |
| Five-agent bootstrap | 2,500 paired frame draws, seed `5701+109` | Grouped R3 interval excludes 0. Grouped R5 increase excludes 0 |
| Sequence 0007 block bootstrap | 12 frames, 3,000 draws, seed `711910` | Mean-error intervals exclude the other endpoint. A 24-frame block lets the four-event joint rate reach 0 |
| Deadline seeds `77109`–`77114` | Packet loss fixed at 0 | Error equals local through 31.5 ms. Updates apply from 32 ms. Incremental energy, jobs, and bytes do not depend on the deadline. Idle baseline does, because the accounting horizon includes the deadline |
| Packet-loss seeds | Deadline fixed at 150 ms | Conservative F0 keeps local’s R2 at every loss rate. At 100% loss both fusion policies match local error |
| Rejected and late updates | 306 deadline and loss runs | 0 labels that lacked an applied update differed from the local prediction. 0 labels were missing |

Intervals are pointwise. They are not adjusted for the number of plotted cells. The 0007 intervals describe one sequence.

## Final validation

These checks are stored in `P1/final_validation/`. The installed fuser still uses `confidence < 0.90`. The alternate rule is a validation script.

At equal error 0.10, one opposing group produces logit `log(9)` and floating-point confidence `0.8999999999999999`. The fuser weight is `4.44e-16` below `log(9)`, so a strict logit comparison rejects it as well. The documented rule accepts when `abs(logit) + 1e-12` reaches `log(0.90 / 0.10)`. On seeds `5701`–`5706` that rule makes three-agent and five-agent F0 match majority on every label. The original rule matches local for three agents: seed `5701` stays at 1,189/12,000 wrong labels, R2 111/4,000, and R3 7/4,000. After the tolerance, that seed is 333/12,000, with R2 and R3 both 111/4,000. Five agents move from 649/20,000, R3 39/4,000, and R5 2/4,000 to the majority result, 195/20,000 and R3 = R5 = 39/4,000. The same tolerance changes 0 of 4,000 decisions on the Table 3 draw and on both Figure 8 groupings at ρ = 0.75.

The upstream suite is 325 passed, 1 skipped, and 23 failed. The skip needs torch. All 23 failures are missing pinned inputs, including `examples/v2v4real_real_seq0007/trace.jsonl`. The five new regressions, kept in this validation folder so `Octopus-main/tests` stays unchanged, all pass. They cover the boundary, a truth flip, shared result IDs, and local retention after a late update.

The synthetic half of `run_e1_multiobjective.py` was run for 3,000 events, 3,000 bootstrap replicates, block length 1, and seed `711911`. All-three-wrong rates are 1.333%, 2.667%, 3.767%, 4.467%, and 5.367%. Mean errors are 9.933%, 9.044%, 8.044%, 6.800%, and 5.367%. Incremental energy is 0.2400, 0.2664, 0.2923, 0.3186, and 0.3448 J/event. Mean latency is 20.000, 24.672, 29.238, 33.892, and 38.514 ms. These match `docs/MULTI_OBJECTIVE_E1.md`. Idle baseline is 32,694.55 J on every cooperation rate.

The deadline and loss grid was executed again, 306 runs, without rewriting `P1/execution_robustness/`. Seed `77109` incremental totals match that folder: 0.24000, 0.25774, and 0.25776 J/frame at zero loss, and 0.24836 J/frame for both fusion policies at 100% loss. Idle baseline is common to all three policies and every seed. It is 2,285.643 J at a 21 ms deadline and 2,288.455 J at 150 ms. The 2.812 J gap is 129 ms times 21.8 W. Packet loss does not change the baseline. At 21 ms, 0.009399 J of fusion work is past the horizon and remains inside the incremental total. From 31.5 ms on, that post-window term is 0.

## Acceptance audit

The two P1 paragraphs in Section 6 are split into the checks below.

| Criterion | Status | Where it stands |
|---|---|---|
| Analytical reuse partitions | Complete, stored outside `P1/` | `reuse_toy.csv` and `ANALYSIS.md` match 2+2+1 and 3+1+1 |
| Three-agent majority and expert cases | Complete | `P1/three_agent/`. Table 3 and Figure 7 match after rounding |
| Five-agent grouped and misgrouped dependence | Complete for Figure 8 | `P1/five_agent/`. The script’s bundled 0007 replay was skipped because `examples/v2v4real_real_seq0007/trace.jsonl` is absent |
| Heterogeneous reliability | Complete | Three-agent rates 0.015, 0.26, 0.32. Five-agent rates 0.055, 0.080, and 0.18 |
| Equal reliability | Complete | `P1/remaining_mechanisms/equal_error_010.csv`. At q = 0.10 the original gate matches local for three agents. `P1/final_validation/threshold_comparison.csv` shows that a `1e-12` nat tolerance matches majority instead. Heterogeneous Table 3 and Figure 8 decisions do not move |
| Independent results and common environmental failures | Complete | Three-agent shock grid and five-agent ρ from 0 to 1, with paired latent draws |
| Exact copies | Complete for prediction reuse | `P1/remaining_mechanisms/result_reuse_vs_correlation.csv`. An exact copied error with one shared result ID matches the correctly grouped distinct IDs. ρ = 0.75 is environmental correlation, not an identical copy. This is not a copied sensor frame |
| Paired seeds | Complete | Seeds `77109`–`77114` cover Table 3, calibration, deadline, and packet loss. Seeds `5701`–`5706` cover the five-agent ρ sweep, equal q = 0.10, and result reuse |
| True versus assumed q | Complete | 63-cell grid in `P1/reliability_robustness/calibration_grid.csv`. The earlier `expert_calibration_grid.csv` stores expert-minus-local deltas only |
| Frame-level uncertainty | Complete, with the stated scope | Frame bootstrap for the synthetic studies. A 12-frame moving block for 0007. These are not nine-scene intervals |
| No oracle at decision time | Complete | `test_regressions.py` flips the stored truth. Fusion actions stay the same and the scored labels change |
| Sweep CSVs and provenance | Complete as run records | Each folder has its CSV and `PROVENANCE.json`, `STUDY_PROVENANCE.json`, or `summary.json`. Source-file hashes were not written |
| Tests of invariants | Complete for the runnable suite | Upstream pytest: 325 passed, 1 skipped, 23 failed on missing pinned traces. New regressions in `P1/final_validation/test_regressions.py`: 5 passed. They cover the threshold boundary, truth independence, shared result IDs, and local fallback. They were not added under `Octopus-main/tests` |
| Simple baselines reported when competitive | Complete | Always-A, majority broadcast, and weighted broadcast are in the tables above |
| E1 sweep with frame reuse | Complete | Regenerated 0007 in `P1/frame_execution/`. Synthetic 3,000-event half in `P1/final_validation/synthetic_e1_3000.csv`, matching the published joint, mean, energy, and latency rows |
| Deadline sweep | Complete | Figure 10, plus six seeds. The 21 ms cliff is a fixed service-time effect |
| Distinct job counts | Complete | `physical_vs_query_accounting.csv`: 221 versus 442 batches. Shared versus distinct result IDs are in `P1/remaining_mechanisms/result_reuse_vs_correlation.csv` |
| Incremental energy separate from idle baseline | Complete | 0007 baseline is 2,230.08 J. The synthetic 3,000-event baseline is 32,694.55 J on every policy. Deadline and loss baselines are in `P1/final_validation/deadline_loss_energy_split.csv`: 2,285.643 J at 21 ms and 2,288.455 J at 150 ms, separate from the incremental totals |
| Late work, link loss, bytes, complete events | Complete | Late updates are counted and unapplied. Loss is a separate grid. Bytes are in both grids. No scored label was missing, so every event was complete |
| Costs kept hypothetical | Complete | Reports and provenance say so |
| No energy claim for an unimplemented OR or disagreement DAG | Complete | Those rules remain offline P0 comparisons. P1 does not assign them latency or joules |
| One accuracy, collective-risk, and cost plot, plus a sensitivity table | Complete | `fig_real_energy_tradeoff.pdf`, `energy_profile_sensitivity_grid.csv`, and `v2v4real_block_bootstrap_sensitivity.csv` |

Nothing in the saved counts disagrees with the manuscript after the printed rounding. Two presentations differ without changing the numbers. The study script’s three-agent figure adds bootstrap bars and labels majority “Majority broadcast”; the manuscript figure does not. The study script’s five-agent figure draws naive majority on a logarithmic R5 axis; Figure 8 draws weighted broadcast on linear axes. The manuscript-style files are the `fig3` and `fig_five_agent_lineage` PDFs.

The expert mean error is 1.167% on the four-query prefix sliced to two queries, and 1.333% on the separate two-query deadline draw. Both use seed `77109`. They are different random sequences, not two evaluations of one trace.

## Limitations

The three-agent and five-agent errors are generated. They are not three-vehicle or five-vehicle captures. Dependence groups and assumed error rates are inputs. They are not estimated from images.

Sequence 0007 is one driving sequence. Its block bootstrap does not generalize to the other eight sequences. The cooperation schedule is one seeded assignment. A 24-frame block lets the unchanged joint count of 4 reach a lower interval endpoint of 0.

Service times are deterministic. The change at 32 ms is not a measured vehicle latency. Packet loss is one transmission attempt, with no retransmission. Lost attempts still consume the modeled radio energy.

The 0007 arrival slots in the nine-sequence trace were shifted so that this sequence occupies slots 0 through 220. Frame identifiers were kept, and the cooperation outcomes match the manuscript. The original `examples/v2v4real_real_seq0007/trace.jsonl` is not in this tree. That missing file, together with the other pinned empirical tables, is why 23 upstream tests fail.

The `1e-12` nat confidence tolerance is a validation comparison. It is not a change to the fuser used for the manuscript tables. Idle baseline energy follows the accounting horizon, so a longer deadline raises baseline joules while the executed work stays the same.

## Supporting files

| Experiment | Runner or original script | Configuration | Main tables | Figures |
|---|---|---|---|---|
| Partitions | `Octopus-main/examples/reuse_toy.py` | q = 0.10 inside the script | `reuse_toy.csv` | None under `P1/` |
| Table 3, Figure 7 | `scripts/run_three_agent_tradeoff_frontier.py` | Seed `77109`, 2,000 frames, shock grid in `P1/three_agent/PROVENANCE.json` | `shock_and_policy_grid.csv`, `table3_comparison.csv`, `paired_frame_bootstrap.csv` | `fig3_three_agent_risk_tradeoff.pdf` |
| Figure 8 | `scripts/run_f0_cvc_parameter_study.py` | Seed `5701`, `--skip-v2v`, `STUDY_PROVENANCE.json` | `lineage_correlation_sweep.csv`, `four_policy_correlation.csv`, `paired_frame_bootstrap_contrasts.csv` | `fig_five_agent_lineage.pdf` |
| Figure 11 | `P1/reliability_robustness/run_reliability.py` | Original true and assumed grids, seed `77109` | `calibration_grid.csv`, `paired_seed_audit.csv` | `fig4_expert_calibration.pdf` |
| Figure 9 | `P1/frame_execution/run_frame_execution.py`, calling `scripts/run_e1_multiobjective.py` | `scenario_frame.json`, `scenario_decision.json`, trace `seq0007_trace.jsonl` | `multiobjective_policy_metrics.csv`, `energy_profile_sensitivity_grid.csv`, `physical_vs_query_accounting.csv` | `fig_real_energy_tradeoff.pdf` |
| Figures 10 and 12, deadline and loss | `P1/execution_robustness/run_execution_robustness.py` | Original deadline list and threshold list, seeds `77109`–`77114` | `deadline_packetloss_grid.csv`, `roi_threshold_physical_cost_grid.csv` | `fig6_deadline_cliff.pdf`, `fig5_sunk_cost_and_roi_reuse.pdf` |
| Equal q, six seeds, result reuse | `P1/remaining_mechanisms/run_remaining.py` | Seeds `5701`–`5706`, q = 0.10, shared result IDs | `equal_error_010.csv`, `five_agent_multiseed.csv`, `result_reuse_vs_correlation.csv` | None |
| Threshold, tests, synthetic E1, energy split | `P1/final_validation/` | Tolerance `1e-12` nat; E1 seed `711911`; same deadline and loss grid | `threshold_comparison.csv`, `synthetic_e1_3000.csv`, `deadline_loss_energy_split.csv`, `upstream_pytest.txt` | None |

Each experiment also has an `ANALYSIS.md` beside those tables. The original templates are `Octopus-main/examples/f0/three_agent_f0.json` and `Octopus-main/examples/energy/v2v4real_0007_energy.json`. The manuscript figure code used as the plotting reference is `Octopus-main/figure_reproduction/make_figures.py` and `make_added_figures.py`.
