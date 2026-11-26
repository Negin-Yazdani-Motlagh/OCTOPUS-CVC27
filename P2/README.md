# P2: CooperScene three-vehicle study

This is the complete record of Phase 2 in Section 6 of `Octopus-main/docs/RESEARCH_GUIDE.md`. The executed experiment is the CooperScene mini set: the published single-agent LiDAR BEVFusion checkpoint, run separately on vehicles 1, 2, and 3, then scored with the existing OCTOPUS three-vehicle importer. Agent 0, the roadside lidar, is not a vehicle. No cooperative or fused checkpoint is used as a vehicle. `Octopus-main` was not edited, and the model was not trained.

The earlier feasibility note is `feasibility/ANALYSIS.md`. The step-by-step notes that this file merges are:

- `cooperscene/setup/README.md`
- `cooperscene/detector_validation/README.md`
- `cooperscene/validation_inference/README.md`
- `cooperscene/test_inference/README.md`
- `cooperscene/evaluation/README.md`

The long audit is `cooperscene/P2_REPORT.md`. The sensitivity write-up is `cooperscene/final_sensitivity/FINDINGS.md`.

Date of the GPU work: 25 November 2026. Machine: Yale Bouchet, node `a1117u29n01`, account `ei235`, project `pi_sjf37`. Work directory: `/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2`.

## What was produced

| Step | Folder | Outcome |
|---|---|---|
| Plan and local environment | `cooperscene/PLAN.md`, `cooperscene/ENVIRONMENT.md` | Official links and the finding that this Mac cannot run the detector |
| Setup smoke test | `cooperscene/setup/` | Checkpoint loads on one test frame. Raw intensity, so the top score is 0.076 |
| Detector check | `cooperscene/detector_validation/` | Official intensity scaling. On one validation frame, 15 of 16 boxes reach BEV IoU 0.5 |
| Validation inference | `cooperscene/validation_inference/` | All 30 validation frames for vehicles 1, 2, and 3. Score 0.10 and the 144-circle grid are frozen here |
| Test export | `cooperscene/test_inference/` | 30 test frames, 1,200 regions, three prediction files, shared truth, and the manifest |
| Evaluation | `cooperscene/evaluation/` | Local, majority, weighted, F0, expert override, and always-A |
| Audit and sensitivity | `cooperscene/audit/`, `cooperscene/final_sensitivity/`, `cooperscene/P2_REPORT.md` | Recount, case figures, temporal blocks, annotation disagreement, and the smoke-frame hold-out |

## Hardware and software

This Mac cannot run the detector: macOS 26.6.2, Apple M4, 16 GB unified memory, no CUDA, no Docker. A separate Windows laptop check (RTX 3050, 4 GB, compute capability 8.6, no `nvcc`) also could not host the 1440×1440 BEV grid. `ENVIRONMENT.md` is the Mac check.

The Bouchet GPU is an NVIDIA B200, compute capability 10.0, 183,359 MiB, driver 580.178.04. `nvidia-smi` reports CUDA 13.0. The allocation was:

```bash
srun --partition=gpu_devel --gpus=b200:1 --cpus-per-task=8 --mem=32G --time=06:00:00 --pty bash
```

The publisher’s pins are Linux, Python 3.10, PyTorch 2.1.1, CUDA 12.1, `mmcv>=2.0,<2.2`, `spconv-cu120`, and BEVFusion gencode through compute 8.6. CUDA 12.1 PTX does not JIT onto Blackwell compute 10.0, so those pins were not used.

The stack that completed the forward pass:

| Piece | Version |
|---|---|
| Module | `PyTorch/2.9.1-foss-2024a-CUDA-12.8.0` |
| PyTorch inside the virtualenv | `torch==2.9.1` from the `cu128` wheel index |
| Python | 3.12 from that module |
| spconv / cumm | 2.3.8 cu128 wheels, compute 10.0 |
| MMCV | 2.2.0, built from source with `MMCV_WITH_OPS=1` and `TORCH_CUDA_ARCH_LIST=10.0` |
| mmdet / mmdet3d | 3.3.0 and 1.4.0, installed `--no-deps` |
| NumPy | 2.2.6. The pin `numpy<1.25` cannot be satisfied on Python 3.12 |

After `module load`, every `/PyTorch/` entry is removed from `LD_LIBRARY_PATH`, the virtualenv `torch/lib` is put first, and `LD_PRELOAD` stays unset. mmdet and mmdet3d refuse MMCV 2.2.0 unless `mmcv_maximum_version` is set to `2.3.0`. Lyft and nuScenes devkits were not installed.

Two model-load details are required on this stack. PyTorch 2.6 and later defaults `torch.load` to `weights_only=True`; this checkpoint pickles `mmengine` history, so the load uses `weights_only=False` after the hash check. The published sparse-convolution weights are stored as `[out, depth, height, width, in]`. This spconv build expects `[depth, height, width, in, out]`. Each 5D tensor is permuted with `permute(1, 2, 3, 4, 0)` when that matches the model, then loaded with `strict=False`. On the validation frame that permute fixed 21 tensors, with 0 still mismatched and 0 missing keys.

Home quota was 107 GiB of 125 GiB, so the install lives on scratch. Delete `/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2` only after no further detector runs are needed. Rebuilding MMCV is the expensive part.

## Downloads

| Item | Check |
|---|---|
| Code | https://github.com/UCR-CISL/CooperScene |
| Mini zip | https://data.ucr.edu/datasets/cooperscene/mini.zip, 2,918,993,095 bytes. The zip has one extra `mini/` directory |
| Weights | `bevfusion_single_lidar.pth`, 115,390,760 bytes |
| SHA-256 | `d71292a772a3f422eb818ab5012a893ee325bffef572524f9c89681eea50f761` |
| Config | `bevfusion_single_lidar.py`, 16,968 bytes, plus the shared `_base_` configs |

Frame counts: train 120, validate 30, test 30. Agents 0, 1, 2, and 3 are present. The code is MIT. The data are CC BY-NC-SA 4.0. Only `bevfusion_single_lidar` was downloaded.

## 1. Setup smoke test

Frame `test/1/1/481410.pcd`, agent 1. Open3D wrote the cloud to a raw float32 `.bin` because `LoadPointsFromFile` cannot read a PCD header. The cloud has 110,245 points. Intensity on that path was left raw, from 3 to 2855.

The model returned 200 boxes. The highest score was 0.076. Those 200 boxes are proposals, not 200 confirmed vehicles. The detection head’s own score threshold is 0.0. `tools/test.py` was not run. Agent 0 was not used.

## 2. Detector validation

Official `convert_pcd_to_bin` divides PCD intensity by 65535. The smoke test skipped that division. `detector_validation/validate_one_frame.py` reran one validation frame, `validate/1/1/481380.pcd`, both ways. The test split was not read, and no cutoff was frozen from this frame.

| Check | Raw intensity | Official intensity / 65535 |
|---|---|---|
| Intensity range | 3 to 2859 | 4.58e-5 to 0.0436 |
| Highest score | 0.125 | 0.889 |
| Best BEV IoU | 0.210 | 0.991 |
| Ground-truth boxes with BEV IoU at least 0.5 | 0 of 16 | 15 of 16 |

All 16 ground-truth boxes on this frame sit inside the ±72 m window. One box remains below IoU 0.5. The published detector detects vehicles once the official preprocessing is used. The smoke-test score of 0.076 was the raw-intensity path on a different frame.

## 3. Validation inference and the frozen protocol

`validation_inference/` runs vehicles 1, 2, and 3 on all 30 validation frames. Intensity uses the official division by 65535. The test split is not read. Matching is one-to-one in the ego lidar frame at BEV IoU 0.50 and 0.70. The predefined score cuts are 0.05, 0.1, 0.3, and 0.5.

The frozen operating point is score **0.10**. On the pooled validation set at one-to-one BEV IoU 0.50 it has precision 0.943, recall 0.980, and F1 0.962. That F1 chooses the cutoff. It is not the reliability rate used by F0.

The world grid is 144 circles of radius 7.5 m on a 15 m lattice with origin (−75 m, −105 m), in frame `cooperscene_global_xy_m`. A circle can contain more than one vehicle, so the label is presence, not identity and not 3D IoU. The centers are stored and reused on the test split. They are not redrawn from test boxes.

Before any test frame is read, `test_inference/freeze_and_export.py` requires all of the following on the validation export. The recorded check is `test_inference/protocol_check.json`, and it passed.

1. Every validation frame has at least one circle inside the ±72 m window of all three vehicles. The observed common-set size was minimum 31, median 33, maximum 40.
2. A box whose horizontal center is within 3 m of the annotating vehicle’s own lidar is dropped from that vehicle’s truth and from its predictions. The rule fails if it would drop more than 10% of a vehicle’s boxes. Vehicle 1 lost 30 of 437 annotated boxes (6.865%) and 30 of 438 predictions at score 0.10 or higher. Vehicles 2 and 3 lost none. The closest annotated box was 0.207 m from its own lidar.
3. The exported truth is the union of the three vehicles’ remaining boxes. On validation, 291 of 1,047 common regions (27.794%) disagree with at least one vehicle’s own annotations. That rate is reported. It does not change the rule.

The reliability rates are those validation region mismatches, `(FP+FN)/1047`:

| Vehicle | Validation region error | False alarms | Misses |
|---|---:|---:|---:|
| 1 | 0.168099 | 4 | 172 |
| 2 | 0.136581 | 3 | 140 |
| 3 | 0.112703 | 5 | 113 |

The importer accepts a fitted-error status only for a train split. These rates are recorded as `unfitted_assumption`. The three run IDs are `bevfusion_single_lidar_test_vehicle1`, `vehicle2`, and `vehicle3`. They share the checkpoint above.

## 4. Test inference

Vehicles 1, 2, and 3 were run separately on the 30 test frames `481410`–`481439`, take 1. Steady-state inference was about 0.05–0.07 s per frame. Peak allocated GPU memory was 598 MiB.

The common set does not move on this clip: every frame has the same 40 of the 144 stored circles. That is 1,200 regions and 3,600 vehicle labels. The shared truth is positive on 327 regions. Test mistakes are almost all misses:

| Vehicle | Region error | Hits | False alarms | Misses | Correct empties |
|---|---:|---:|---:|---:|---:|
| 1 | 153/1,200 = 0.1275 | 177 | 3 | 150 | 870 |
| 2 | 77/1,200 = 0.0642 | 250 | 0 | 77 | 873 |
| 3 | 104/1,200 = 0.0867 | 226 | 3 | 101 | 870 |

These test rates were not written back into the protocol. Vehicle 2 is the best vehicle on the test split. The declared expert stays vehicle 3, because its validation rate is the lowest.

Importer files, all in `cooperscene/test_inference/`:

| File | Role |
|---|---|
| `vehicle_1_predictions.jsonl`, `vehicle_2_predictions.jsonl`, `vehicle_3_predictions.jsonl` | One binary prediction per region |
| `ground_truth.jsonl` | The shared union label |
| `predictions.jsonl` | The merged rows |
| `manifest.json` | Run IDs, validation rates, and the checkpoint hash |
| `test_boxes_vehicle_*.jsonl` | Boxes, scores, and poses |
| `protocol_check.json` | The gate that ran before the test split |

## 5. Evaluation

`Octopus-main/scripts/run_three_vehicle_real_study.py prepare` accepted the export: 30 frames, 1,200 regions, three distinct run IDs, one shared truth file. `evaluate` scored local, majority, and F0 at confidence 0.75, 0.85, 0.90, 0.95, and 0.99. Weighted broadcast, the P1 expert override, and always-A were scored on the same prepared trace. Energy and latency in `evaluation/stock_study/comparison.csv` are the hypothetical E1 profile, not a measurement from the B200.

Prepared outputs are in `cooperscene/evaluation/prepared/`: `trace.jsonl`, `scenario.json`, and `PROVENANCE.json`.

| Policy | Mean error | R2 | R3 | Joint false alarms | Joint misses | Corrections | Introduced errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| Local | 334/3,600 = 9.278% | 36/1,200 = 3.000% | 0/1,200 | 0 | 0 | 0 | 0 |
| Majority | 108/3,600 = 3.000% | 36/1,200 = 3.000% | 36/1,200 = 3.000% | 1 | 35 | 262 | 36 |
| Weighted | 108/3,600 = 3.000% | 36/1,200 = 3.000% | 36/1,200 = 3.000% | 1 | 35 | 262 | 36 |
| Conservative F0 | 217/3,600 = 6.028% | 36/1,200 = 3.000% | 32/1,200 = 2.667% | 0 | 32 | 149 | 32 |
| Expert override | 217/3,600 = 6.028% | 36/1,200 = 3.000% | 32/1,200 = 2.667% | 0 | 32 | 149 | 32 |
| Always vehicle 3 | 312/3,600 = 8.667% | 104/1,200 = 8.667% | 104/1,200 = 8.667% | 3 | 101 | 197 | 175 |

Of the 1,200 regions, 902 have no local error, 262 have exactly one, and 36 have exactly two. None have all three wrong.

Majority and weighted broadcast make the same 3,600 decisions. They fix every single-vehicle mistake. On each of the 36 double errors they overwrite the one correct vehicle: 35 lost detections and 1 false alarm. The three validation rates are close enough that a 2–1 split never changes side.

Conservative F0 is confidence 0.90, at least two independent groups, at least two supporting groups, conflict fraction at most 0.40, and source error at most 0.25. It accepts 1,083/1,200 = 90.250% of regions. It adopts a label only when vehicles 2 and 3 already agree. That corrects vehicle 1 on 149 regions and erases vehicle 1’s correct detection on 32 occupied regions. Vehicles 2 and 3 do not change a label. F0 rejects the one double false alarm.

The stock threshold list agrees. At 0.75, F0 accepts every region and matches majority. At 0.85, mean error is 0.0489 and R3 is 0.0275. At 0.90 it matches the conservative row. At 0.95 and 0.99 it changes no label, so the error stays at 334/3,600, while still accepting the 902 unanimous regions.

The expert override fires only when the declared expert error is at most 0.05 and F0’s only objection is insufficient independent support. Vehicle 3’s validation rate is 0.1127, so the override never replaces an F0 rejection. Always-A copies vehicle 3 onto the other two vehicles.

Paired frame bootstrap, 2,000 draws of the 30 frames, seed 77232. The interval is the 2.5 and 97.5 percentiles of the difference from local.

| Policy minus local | Mean error | R2 | R3 |
|---|---|---|---|
| Majority and weighted | [−0.0675, −0.0578] | [0, 0] | [+0.0217, +0.0392] |
| Conservative F0 and expert override | [−0.0350, −0.0297] | [0, 0] | [+0.0192, +0.0342] |
| Always vehicle 3 | [−0.0114, −0.0003] | [+0.0508, +0.0625] | [+0.0792, +0.0950] |

R2 does not move because majority and F0 never change which regions have two or more wrong vehicles. They only turn some of those regions into three-vehicle errors.

Local error correlation is −0.0695 for vehicles 1 and 2, −0.1089 for 1 and 3, and +0.3061 for 2 and 3. Putting all three vehicles in one dependence group makes F0 accept nothing, and the error returns to 9.278%. The gain in the table depends on treating the three run IDs as separate evidence. The shared checkpoint and the positive correlation between vehicles 2 and 3 are why that treatment is an assumption.

Against P1 Table 3 (shock 0.18, seed 77109, 4,000 synthetic queries), the signs match for majority and for conservative F0: mean error falls and R2 stays on the local curve. The sizes differ. P1’s local error was 20.025%, and most of those errors were already inside an R2 event, so majority barely moved the mean. Here 262 of 298 imperfect regions are single-vehicle mistakes, so the vote cuts the mean from 9.278% to 3.000%. P1’s F0 moved R3 from 0.200% to 0.400%. Here F0 accepts 32 of 35 double misses, so R3 moves from 0 to 2.667%. P1’s expert override copied the expert on every query because the declared error was 1.5%. At 11.3%, the same rule does not fire.

## 6. Audit

`cooperscene/audit/audit_final.py` recomputed every label from the export. It matched `evaluation/metrics.json` and the stock correction counts, and a one-frame block bootstrap with the same seed reproduced the intervals above. The script stops if any of those checks fail.

The 35 detections erased by majority sit on five cells of the same 40-circle grid. Twenty-one are the cell at (−45 m, 0 m). F0 keeps 3 of the 35, all at (30 m, 0 m), where only vehicle 3 voted occupied. The drawings are in `cooperscene/audit/figures/`.

| Frame | Region | What happened |
|---|---|---|
| 481410 | `grid_031` at (−45 m, 0 m) | Vehicle 1 voted occupied. Majority and F0 both wrote empty |
| 481411 | `grid_091` at (30 m, 0 m) | Only vehicle 3 voted occupied. Majority wrote empty. F0 kept the local vote |

Neighboring circles, 15 m apart on one axis, have error correlation +0.258 for vehicle 1 and +0.294 for vehicle 3. The same circle is usually wrong on the next frame: lag-1 correlation is 0.9768, 0.8475, and 0.9563 for vehicles 1, 2, and 3. A moving block of consecutive frames, seed 77232 and 2,000 draws, leaves the majority and F0 mean-error intervals below zero through 10-frame blocks. Always-A’s mean-error interval includes zero once the block is two frames or longer. The R3 intervals stay above zero at every block length.

## 7. Sensitivity

These checks do not replace the 30-frame table. The score, radius, grid, and reliability rates stay frozen. Detector inference was not rerun.

The 291 validation disagreements are annotation coverage, not the 3 m ego rule. Replaying the official rotation, the ego drop, the ±72 m window, and the 144 stored centers returns the same 291 of 1,047. Vehicle 1 misses 168 of the union hits, vehicle 2 misses 143, and vehicle 3 misses 113. Restoring vehicle 1’s 30 ego-dropped boxes removes 0 disagreements. Across 1,274 stored ego boxes, the largest residual of the official rotation is 2.132e-14 m. The 291 region-frames sit on 15 repeated centers. A joint miss means all three detectors voted empty where the union is occupied. On validation, 291 of 336 occupied union regions are absent from at least one vehicle’s own annotations, so a joint miss is not by itself evidence that all three annotation sets contained the same object.

Holding out the smoke-test frame 481410 leaves 29 frames, 1,160 regions, and 3,480 labels. That frame had 11 wrong local labels out of 120. Majority moves from 108/3,600 to 105/3,480, and conservative F0 from 217/3,600 to 210/3,480. R3 moves from 36/1,200 to 35/1,160 for majority and from 32/1,200 to 31/1,160 for F0. The ordering does not change. The primary claims stay on all 30 frames.

A secondary rescore keeps only test regions where every vehicle’s kept annotations agree with the union. It retains 903 regions and 2,709 labels, and drops 297 positive regions. On that subset local error is 6/2,709 = 0.221%, majority is 3/2,709, and every policy has 0 joint misses. The 35 double misses in the primary table sit in the dropped regions. This subset does not replace the union table.

## What this phase does not claim

The clip is one take and 30 frames. The metric is presence inside a 7.5 m circle, not 3D detection mAP. The three exports share a checkpoint, and vehicles 2 and 3 have positively correlated errors. Counting the three run IDs as independent groups is an assumption; the one-group rerun removes the F0 gain. Energy and latency are hypothetical. The B200 run is not the publisher’s CUDA 12.1 image. The one-frame IoU check is the evidence that the adapted stack still produced real boxes.
