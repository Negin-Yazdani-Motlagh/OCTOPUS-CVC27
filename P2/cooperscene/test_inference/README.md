# Test inference

The frozen rules are in `PROTOCOL.md`. `freeze_and_export.py` checks them on the validation export first. Test frames are read only after that check passes.

The test split is then run separately for vehicles 1, 2, and 3 with official intensity scaling. Region labels use the frozen score 0.10, radius 7.5 m, and the 144 stored validation centers. Parameters are not changed from the test result.

Outputs:

| File | Role |
|---|---|
| `protocol_check.json` | Coverage, ego-vehicle audit, label disagreement, validation region-error rates |
| `test_boxes_vehicle_1.jsonl` and the same for 2 and 3 | Boxes, scores, poses, and run IDs |
| `vehicle_1_predictions.jsonl` and the same for 2 and 3 | Importer per-vehicle binary predictions |
| `ground_truth.jsonl` | One shared truth label per region |
| `predictions.jsonl` | Merged importer rows |
| `manifest.json` | Provenance, checkpoint SHA-256, and the three distinct run IDs |

## Run

On the GPU node, after this folder is copied to scratch:

```bash
sed -i 's/\r$//' /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/test_inference/run_test_inference.sh
bash /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/test_inference/run_test_inference.sh
```

If the check fails, the script prints `PROTOCOL_GATE_FAILED` and `TEST_INFERENCE_NOT_STARTED`.

## Result

The validation gate passed, and the test export finished on 25 November 2026. Thirty frames each for vehicles 1, 2, and 3. The frozen score, radius, and grid were not changed after seeing the test frames.

The export has 1,200 region rows, 40 per frame on average, drawn from the 144 frozen circles that fell inside all three detector windows. On those regions the shared truth is positive 327 times. The mistakes are almost all misses:

| Vehicle | Region error | Hits | False alarms | Misses | Correct empties |
|---|---|---|---|---|---|
| 1 | 0.128 | 177 | 3 | 150 | 870 |
| 2 | 0.064 | 250 | 0 | 77 | 873 |
| 3 | 0.087 | 226 | 3 | 101 | 870 |

These test rates were not written back into the protocol. The manifest's error rates are the validation region rates on 1,047 common regions: vehicle 1 at 0.1681, vehicle 2 at 0.1366, and vehicle 3 at 0.1127.

Steady-state inference was about 0.05–0.07 s per frame. Peak allocated GPU memory was 598 MiB.

The importer files are in this folder and on the cluster at `/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/test_inference/`: `predictions.jsonl`, `ground_truth.jsonl`, `vehicle_1_predictions.jsonl`, `vehicle_2_predictions.jsonl`, `vehicle_3_predictions.jsonl`, `manifest.json`, and `protocol_check.json`.

## Three-vehicle study

The completed export was scored with `Octopus-main/scripts/run_three_vehicle_real_study.py`. `prepare` accepted 30 frames and 1,200 regions. `evaluate` then scored local, majority, and the F0 threshold list. Weighted broadcast, expert override, and always-A were scored on that same prepared trace. Detector inference was not rerun. The frozen protocol and `Octopus-main` were left unchanged.

The expert is vehicle 3, the lowest validation rate. Vehicle 2's lower test error, 0.0642, was not used.

| Policy | Mean error | R2 | R3 | Joint false alarms | Joint misses | Corrections | Introduced errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| Local | 0.0928 | 0.0300 | 0.0000 | 0 | 0 | 0 | 0 |
| Majority | 0.0300 | 0.0300 | 0.0300 | 1 | 35 | 262 | 36 |
| Weighted | 0.0300 | 0.0300 | 0.0300 | 1 | 35 | 262 | 36 |
| Conservative F0 | 0.0603 | 0.0300 | 0.0267 | 0 | 32 | 149 | 32 |
| Expert override | 0.0603 | 0.0300 | 0.0267 | 0 | 32 | 149 | 32 |
| Always-A | 0.0867 | 0.0867 | 0.0867 | 3 | 101 | 197 | 175 |

Locally, 262 regions have one wrong vehicle and 36 have two. None have all three wrong. Majority and weighted broadcast fix every single-vehicle mistake and, on each double error, overwrite the one correct vehicle. The validation rates are close enough that weighting never changes a 2–1 split. Conservative F0 matches the stock script at confidence 0.90: it accepts 90.25% of regions, keeps R2 at 0.0300, and turns 32 of the 35 double misses into three-vehicle misses. The 36 double-error regions are 35 double misses and one double false alarm, and F0 rejects that false alarm. The override stays idle because vehicle 3's validation rate is 0.1127, above the 0.05 firing limit, so it matches F0. Always-A copies vehicle 3 on every region.

Paired frame bootstrap, 2,000 draws of the 30 frames, seed 77232, versus local:

| Policy minus local | Mean error | R2 | R3 |
|---|---|---|---|
| Majority | [−0.0675, −0.0578] | [0, 0] | [+0.0217, +0.0392] |
| Weighted | [−0.0675, −0.0578] | [0, 0] | [+0.0217, +0.0392] |
| Conservative F0 | [−0.0350, −0.0297] | [0, 0] | [+0.0192, +0.0342] |
| Expert override | [−0.0350, −0.0297] | [0, 0] | [+0.0192, +0.0342] |
| Always-A | [−0.0114, −0.0003] | [+0.0508, +0.0625] | [+0.0792, +0.0950] |

The R2 interval is exactly zero because majority and F0 never change which regions have two or more wrong vehicles. They only turn some of those regions into three-vehicle errors.

Local error correlation is −0.070 for vehicles 1 and 2, −0.109 for 1 and 3, and +0.306 for 2 and 3. With all three vehicles in one dependence group, F0 accepts nothing and the error returns to 0.0928. Distinct run IDs were checked as three different strings. The shared checkpoint and the 0.31 correlation are why those strings are not treated as independent errors.

Against P1 Table 3, the signs match. Majority lowered mean error, left R2 unchanged, and moved that R2 mass into R3. Conservative F0 lowered mean error and left R2 unchanged. The sizes differ: P1's local error was 0.2003 under a designed shock, and its F0 barely moved R3 (0.0020 to 0.0040). Here most imperfect regions are single-vehicle mistakes, so the vote removes them, while F0 accepts 32 of the 35 double misses and rejects the one double false alarm. There are 36 double-error regions in all. P1's expert override reached 0.0138 because the declared expert error was 1.5%. At 11.3%, the same rule does not fire.

The full tables are in `../evaluation/README.md`, `../evaluation/FINDINGS.md`, and `../evaluation/metrics.json`. The audit is in `../P2_REPORT.md`.

## Final audit

`../audit/audit_final.py` recomputed all 3,600 labels from this export. The totals match `../evaluation/metrics.json` and the stock correction counts in `comparison.csv`. A one-frame block bootstrap with seed 77232 reproduced the published intervals. The score, radius, and grid were not changed. Detector inference was not rerun.

Every test frame contains the same 40 circles, all on the frozen 7.5 m lattice. The validation gate that ran before these frames had no failure. Vehicle 1's ego drop was 30/437 annotated boxes. Vehicles 2 and 3 lost none. On validation, 291/1,047 common regions disagreed with the shared union. The exported test truth is that union: 327/1,200 regions are positive, and `ground_truth.jsonl` matches the merged file on every row.

Majority fixes all 262 single-vehicle mistakes and, on all 36 double mistakes, overwrites the one correct vehicle. Those overwrites are 35 lost detections and 1 false alarm. Weighted broadcast makes the same 3,600 decisions. Conservative F0 accepts a 2–1 split only when vehicles 2 and 3 already agree. It corrects vehicle 1 on 149 regions and erases vehicle 1's correct detection on 32. Vehicles 2 and 3 do not change a label under F0. The expert override matches F0 on every label.

The 35 lost detections sit on five cells. Twenty-one are (−45 m, 0 m). The drawings are in `../audit/figures/`.

| Frame | Region | What happened |
|---|---|---|
| 481410 | `grid_031` at (−45 m, 0 m) | Vehicle 1 voted occupied. Majority and F0 both wrote empty. |
| 481411 | `grid_091` at (30 m, 0 m) | Vehicle 3 voted occupied. Majority wrote empty. F0 kept the local vote. |

Neighboring circles, 15 m apart on one axis, have error correlation +0.258 for vehicle 1 and +0.294 for vehicle 3. The same circle is wrong on the next frame with lag-1 correlation 0.85 to 0.98. A moving-block bootstrap, seed 77232 and 2,000 draws, leaves the majority and F0 mean-error intervals below zero through 10-frame blocks. Always-A's mean-error interval includes zero once the block is two frames or longer. With all three vehicles in one dependence group, F0 accepts nothing and the error returns to 0.0928.

## Final sensitivity

These checks do not replace the 30-frame table. The score, radius, and grid were not changed. The write-up is `../final_sensitivity/FINDINGS.md`, and the same section is in `../P2_REPORT.md`.

All 291 annotation disagreements sit inside the 336 occupied union regions, so 45 occupied regions are in every vehicle's own labels and the 711 empty regions agree. The ego rule cannot explain that rate. Vehicle 1 lost 30 boxes and vehicles 2 and 3 lost none. A point on this lattice meets at most two circles, so restoring every dropped box can repair at most 60 disagreements, and only for vehicle 1. At least 231 disagreements remain, and those are annotation coverage. The one-frame world-from-ego residual was 2.13e-14 m. A per-vehicle map was not drawn: the validation box files are not in this folder. A joint miss means all three detectors voted empty where the union is occupied. On validation, most occupied union regions are not occupied in every vehicle's own annotations.

The moving-block intervals for R3 minus local stay above zero at 1, 2, 5, and 10 frames for every non-local policy. Seed 77232, 2,000 draws.

| Policy minus local | 1 frame | 2 frames | 5 frames | 10 frames |
|---|---|---|---|---|
| Majority | [+0.0217, +0.0392] | [+0.0192, +0.0408] | [+0.0158, +0.0367] | [+0.0158, +0.0333] |
| Weighted | [+0.0217, +0.0392] | [+0.0192, +0.0408] | [+0.0158, +0.0367] | [+0.0158, +0.0333] |
| Conservative F0 | [+0.0192, +0.0342] | [+0.0175, +0.0358] | [+0.0158, +0.0333] | [+0.0150, +0.0317] |
| Expert override | [+0.0192, +0.0342] | [+0.0175, +0.0358] | [+0.0158, +0.0333] | [+0.0150, +0.0317] |
| Always-A | [+0.0792, +0.0950] | [+0.0767, +0.0983] | [+0.0750, +0.0983] | [+0.0750, +0.0967] |

Longer blocks make the R3 rise less precise. They do not remove it. That rise is unfavorable for the fusion rules.

Holding out the smoke-test frame 481410 leaves 1,160 regions. That frame had 11 wrong local labels out of 120. Majority moves from 108/3,600 to 105/3,480, and its R3 from 36/1,200 to 35/1,160. Conservative F0 moves from 217/3,600 to 210/3,480, and its R3 from 32/1,200 to 31/1,160. Joint false alarms do not change. Dropping the frame does not improve the policies or change their order. The primary claims stay on all 30 frames. The figure is `../final_sensitivity/figures/frame_exclusion.png`.
