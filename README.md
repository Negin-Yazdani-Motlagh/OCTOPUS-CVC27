# OCTOPUS validation

Reproduction and extension of the OCTOPUS / CVC reliability-aware coordination study. The three phases follow Section 6 of the OCTOPUS research guide. OCTOPUS-Sim 0.7.1 was used as shipped. The original source, original configurations, and the manuscript were not edited. Truth is used only for scoring.

A region label is presence inside a circle. It is not 3D detection mAP and not an object identity match. Energy and latency in P1, and the energy column in P2, are the hypothetical E1 profile, not a measurement from a radio or a GPU.

| Phase | Question | Where to start |
|---|---|---|
| P0 | Two real vehicle detectors on nine V2V4Real sequences | [P0/P0_REPORT.md](P0/P0_REPORT.md) |
| P1 | Controlled three-agent and five-agent mechanisms, then deadlines and energy | [P1/P1_REPORT.md](P1/P1_REPORT.md) |
| P2 | Three real CooperScene vehicles, from a single-agent LiDAR checkpoint | [P2/P2_REPORT.md](P2/P2_REPORT.md) |

## P0: two vehicles, V2V4Real

Nine DMSTrack sequences, commit `d3b9949499c8e68ea33060873bd1cb95b6d4d323`. The published setting is radius 7.5 m and score 0.30: 1,993 frames, 3,986 queries, and 7,972 labels.

| Detector | Errors |
|---|---|
| Ego | 670/3,986 = 16.81% |
| Partner | 481/3,986 = 12.07% |
| CoBEVT | 325/3,986 = 8.15% |
| Late fusion | 194/3,986 = 4.87% |
| Both local detectors | 105/3,986 = 2.63% |
| Local mean | 1,151/7,972 = 14.44% |

Sequence 0007 matches the guide: 221 frames, local mean error 200/884 = 22.62%, late fusion 32/884 = 3.62%. Conservative two-agent F0 changes 0 of 7,972 labels, because one supporting group cannot meet the requirement of two. Late fusion lowers mean error in every sequence and raises the two-agent error rate in eight. That increase is joint false alarms. A sequence bootstrap of 20,000 draws, seed `20261118`, puts late fusion minus local at −9.571 percentage points of mean error, interval [−15.272, −5.248], and +2.233 points of R2, interval [+0.882, +3.613].

| Folder | Contents |
|---|---|
| `v2v4real_all/` | Trace, provenance, and the nine-sequence counts |
| `class_analysis/` | Positive and negative queries |
| `policy_comparison/` | Local, late fusion, CoBEVT, disagreement, OR, and AND |
| `f0_real/` | Two-agent F0, with zero label changes |
| `statistical_analysis/` | Sequence bootstrap |
| `spatial_sensitivity/` | Radius and score grid |
| `spatial_audit/` | The harmful queries and the top-down figures |
| `object_validation/` | Bird’s-eye-view IoU of the 29 harmful rows |
| `acceptance_audit/` | Paired outcomes, always-ego, always-partner, and temporal blocks |

## P1: controlled mechanisms and execution

The manuscript numbers match after ordinary rounding. Table 3, shock 0.18, seed `77109`, is 4,000 queries and 12,000 labels.

| Policy | Mean error | R2 | R3 |
|---|---:|---:|---:|
| Local | 2,403/12,000 = 20.025% | 792/4,000 = 19.800% | 8/4,000 = 0.200% |
| Majority | 2,376/12,000 = 19.800% | 792/4,000 = 19.800% | 792/4,000 = 19.800% |
| Conservative F0 | 1,639/12,000 = 13.658% | 792/4,000 = 19.800% | 16/4,000 = 0.400% |
| Expert override | 165/12,000 = 1.375% | 55/4,000 = 1.375% | 55/4,000 = 1.375% |

Majority lowers the average and turns every two-agent mistake into a three-agent mistake. Conservative F0 lowers the average and leaves R2 on the local curve. On this seed the expert override copies the reliable agent on every query. At equal error 0.10 the published 0.90 comparison misses the boundary by a floating-point gap, so three-agent F0 matches local. A validation-only tolerance of 1e-12 nat makes it match majority. That tolerance was not written into the original fuser.

Figure 8, five agents at correlation 0.75, separates a correctly grouped clique from three copies treated as independent. On regenerated sequence 0007, full cooperation moves mean error from 22.62% to 3.62% and incremental energy from 0.160 to 0.243 J/frame. The deadline cliff is 32 ms. A late or rejected update does not erase the local label and does not refund the completed job.

| Folder | Contents |
|---|---|
| `three_agent/` | Table 3 and Figure 7 |
| `five_agent/` | Figure 8 |
| `reliability_robustness/` | Figure 11, expert calibration |
| `frame_execution/` | Figure 9 on sequence 0007 |
| `execution_robustness/` | Figures 10 and 12, deadline, and packet loss |
| `remaining_mechanisms/` | Six seeds, equal error 0.10, and shared result IDs |
| `final_validation/` | Threshold tolerance, synthetic 3,000-event E1, and idle versus incremental energy |

## P2: three real CooperScene vehicles

The CooperScene mini set, 30 test frames of one take. The published single-agent LiDAR BEVFusion checkpoint was run separately on vehicles 1, 2, and 3. Agent 0, the roadside lidar, is not counted. A fused cooperative output is not counted. The same checkpoint, SHA-256 `d71292a772a3f422eb818ab5012a893ee325bffef572524f9c89681eea50f761`, produced all three files, with three different run IDs.

The score 0.10 and the 144-circle grid were frozen on the validation split. Radius is 7.5 m. The test export has 1,200 common regions and 3,600 labels. Reliability rates are the validation region errors: 0.168, 0.137, and 0.113. They were not refit on the test split.

| Policy | Mean error | R2 | R3 |
|---|---:|---:|---:|
| Local | 334/3,600 = 9.278% | 36/1,200 = 3.000% | 0/1,200 |
| Majority and weighted | 108/3,600 = 3.000% | 36/1,200 = 3.000% | 36/1,200 = 3.000% |
| Conservative F0 and expert override | 217/3,600 = 6.028% | 36/1,200 = 3.000% | 32/1,200 = 2.667% |
| Always vehicle 3 | 312/3,600 = 8.667% | 104/1,200 = 8.667% | 104/1,200 = 8.667% |

F0 corrects vehicle 1 only when vehicles 2 and 3 already agree. The expert override does not fire, because vehicle 3’s validation error is above 0.05. Putting all three vehicles in one dependence group makes F0 accept nothing, and the error returns to the local 9.278%. The signs match P1: mean error falls, R2 stays put, and R3 rises.

The detector did not run on the publisher’s CUDA 12.1 image. The GPU was an NVIDIA B200, and the stack was PyTorch 2.9.1 with CUDA 12.8. Official intensity scaling, division by 65535, was required. On one validation frame that scaling matched 15 of 16 ground-truth boxes at bird’s-eye-view IoU 0.50. Peak allocated memory on the test run was 598 MiB.

The step-by-step account is [P2/README.md](P2/README.md). The feasibility note written before the download is [P2/feasibility/ANALYSIS.md](P2/feasibility/ANALYSIS.md).

| Folder | Contents |
|---|---|
| `cooperscene/setup/` | Why the official pins did not run, and the one-frame smoke test |
| `cooperscene/detector_validation/` | Raw intensity against the official scaling |
| `cooperscene/validation_inference/` | The 30 validation frames and the frozen cutoff |
| `cooperscene/test_inference/` | The three prediction files, shared truth, and manifest |
| `cooperscene/evaluation/` | Local, majority, F0, and the stock study script |
| `cooperscene/audit/` | Recount and the lost-detection figures |
| `cooperscene/final_sensitivity/` | Annotation disagreement, temporal blocks, and the smoke-frame hold-out |

## What this repository does not contain

`run_all.py` and top-level `scripts/`, `configs/`, `results/`, `provenance/`, and `tests/` directories were not part of these validation folders. Each phase keeps its own scripts and outputs inside `P0/`, `P1/`, and `P2/`. Figures are stored next to the experiment that produced them.

The CooperScene mini archive and the checkpoint weights are not in this repository. The test export is the JSONL already scored by the importer. Dataset files remain under their upstream license. The CooperScene code is MIT and the data are CC BY-NC-SA 4.0.
