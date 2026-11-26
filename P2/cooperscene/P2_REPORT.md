# P2 report: CooperScene three-vehicle experiment

This report covers the real three-vehicle study in Section 6 of `Octopus-main/docs/RESEARCH_GUIDE.md`. The detector export was already frozen. This audit rescores that export. It does not rerun detector inference, does not change the score, radius, or grid, and does not edit `Octopus-main` or the manuscript.

The run is one CooperScene mini take, test frames `481410`–`481439`. There are 30 frames, 40 common regions per frame, and 1,200 regions. Each region is one decision for vehicles 1, 2, and 3, so the label count is 3,600. Truth is used only for scoring. Energy and latency in `evaluation/stock_study/comparison.csv` remain the hypothetical E1 profile.

## Methodology

The frozen protocol is `test_inference/PROTOCOL.md`.

| Choice | Value | Where it came from |
|---|---|---|
| Score | 0.10 | Highest pooled object F1 on validation. Not used as the reliability rate. |
| Radius | 7.5 m | Named before the test split. |
| Spacing | 15 m | One diameter. |
| Origin | (−75 m, −105 m) | Validation lattice. |
| Circles | 144 stored centers | Not redrawn from test boxes. |
| Reliability | Validation region error | Vehicle 1: 0.168099. Vehicle 2: 0.136581. Vehicle 3: 0.112703. Each is `(FP+FN)/1047`. |

A region is positive when any kept vehicle center lies inside the circle. That is presence, not identity and not 3D IoU. The shared truth is the union of the three vehicles' boxes after the ego-vehicle drop. Agent 0, the roadside lidar, is absent. The same checkpoint, SHA-256 `d71292a772a3f422eb818ab5012a893ee325bffef572524f9c89681eea50f761`, produced all three exports. The run IDs differ: `bevfusion_single_lidar_test_vehicle1`, `vehicle2`, and `vehicle3`.

`Octopus-main/scripts/run_three_vehicle_real_study.py prepare` built `evaluation/prepared/` from `predictions.jsonl` and `manifest.json`. `evaluate` then ran local, majority, and F0 at confidence 0.75, 0.85, 0.90, 0.95, and 0.99. The stock command does not emit weighted broadcast, the expert override, or always-A. Those three are scored on the same prepared trace with the P1 classes `AlwaysVote` and `DiagnosticExpertOverride`. Conservative F0 is `SelectiveFuser` at the scenario values: confidence 0.90, at least two independent groups, at least two supporting groups, conflict fraction at most 0.40, and source error at most 0.25. The expert is vehicle 3 because its validation rate is the lowest. Ties would break toward the smaller vehicle id. Test error was not used.

`audit/audit_final.py` recomputed every label from the export. It matched `evaluation/metrics.json` on mean error, R2, R3, joint false alarms, joint misses, corrections, and introduced errors. It matched `comparison.csv` on local, majority, and `f0_0.900`, including the paired correction counts. A one-frame block bootstrap with seed `77232` and 2,000 draws reproduced the published intervals. The script stops if any of those checks fail.

## File, coverage, ego, and ground-truth checks

The merged predictions, the three per-vehicle files, `ground_truth.jsonl`, and the prepared trace agree on all 1,200 keys `(take 1, frame, roi)`. Every prediction and every truth bit is 0 or 1. Every center lies on the frozen lattice, and every radius is 7.5 m. A region id keeps one center for the whole take. The thirty frame tokens are consecutive.

On the test split the common set does not move. Each frame contains the same 40 circles, so 40 of the 144 stored centers are inside all three detector windows throughout `481410`–`481439`. The validation gate, which had to pass before those frames were read, saw a varying common set: minimum 31, median 33, maximum 40, and no frame with an empty set. The ±72 m window was applied with the vehicles' poses at export time. Those poses are not in the importer files, so this audit checks the exported lattice rather than replaying the window test.

The ego rule drops a box whose horizontal center is within 3 m of the annotating vehicle's own lidar, from that vehicle's ground truth and from its predictions. The recorded check is the validation gate. Vehicle 1 lost 30 of 437 annotated boxes (6.865%) and 30 of 438 boxes at score 0.10 or higher (6.849%). Vehicles 2 and 3 lost none. All four fractions are under the 10% cap, and `protocol_check.json` records no gate failure. The closest annotated box on validation was 0.207 m from its own lidar, which is the case the rule is there to remove. Test ego-drop counts were not written beside the region rows, so they are not recomputed here. The exported labels are the labels after that rule.

Ground truth is one shared bit per region. On validation, 291 of 1,047 common regions (27.794%) have at least one vehicle whose own annotations disagree with the union. The export keeps the union. On test, `ground_truth.jsonl` matches the merged file on every row: 327 of 1,200 regions are positive. The per-vehicle files carry predictions only, so a second truth cannot disagree with the shared file inside this export.

## Results

Local error is 334/3,600 = 9.278%. That is 153/1,200 for vehicle 1 (3 false alarms and 150 misses), 77/1,200 for vehicle 2, and 104/1,200 for vehicle 3. R2 is 36/1,200 = 3.000%. R3 is 0/1,200. Of the 1,200 regions, 902 have no local error, 262 have exactly one, and 36 have exactly two.

| Policy | Mean error | R2 | R3 | Joint false alarms | Joint misses | Corrections | Introduced errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| Local | 334/3,600 = 9.278% | 36/1,200 = 3.000% | 0/1,200 = 0 | 0 | 0 | 0 | 0 |
| Majority | 108/3,600 = 3.000% | 36/1,200 = 3.000% | 36/1,200 = 3.000% | 1 | 35 | 262 | 36 |
| Weighted | 108/3,600 = 3.000% | 36/1,200 = 3.000% | 36/1,200 = 3.000% | 1 | 35 | 262 | 36 |
| Conservative F0 | 217/3,600 = 6.028% | 36/1,200 = 3.000% | 32/1,200 = 2.667% | 0 | 32 | 149 | 32 |
| Expert override | 217/3,600 = 6.028% | 36/1,200 = 3.000% | 32/1,200 = 2.667% | 0 | 32 | 149 | 32 |
| Always-A | 312/3,600 = 8.667% | 104/1,200 = 8.667% | 104/1,200 = 8.667% | 3 | 101 | 197 | 175 |

Weighted broadcast equals majority on all 3,600 labels. The three validation rates are close enough that a 2–1 split never changes side. The expert override equals conservative F0 on all 3,600 labels. Vehicle 3's validation rate, 0.112703, is above the 0.05 firing limit, so the override never replaces an F0 rejection. Always-A copies vehicle 3, and 312/3,600 is that vehicle's 104 errors repeated three times.

The stock script agrees. `f0_0.750` accepts every region and matches majority: 108/3,600, with R2 and R3 both 36/1,200. `f0_0.900` matches the conservative row above and accepts 1,083/1,200 = 90.250%. `f0_0.950` and `f0_0.990` change no label, so the error stays at 334/3,600. They still accept the unanimous regions, 902/1,200 = 75.167%, and those acceptances do not move a bit.

## Paired transitions

Every changed label was checked against the local bit and the shared truth.

Majority has only three event transitions. The 902 clean regions stay clean. All 262 single-error regions become clean: the one wrong vehicle is corrected, and the two correct vehicles stay correct. All 36 two-error regions become three-error regions: the one correct vehicle is overwritten, and the two wrong vehicles stay wrong. Those 36 overwrites are 35 lost correct detections and 1 introduced false alarm.

| Who is solely wrong | Regions | F0 accepts |
|---|---:|---:|
| Vehicle 1 | 149 | 149 |
| Vehicle 2 | 42 | 0 |
| Vehicle 3 | 71 | 0 |

| Who is wrong together | Regions | What the truth is | F0 accepts |
|---|---:|---|---:|
| Vehicles 2 and 3 | 32 | Occupied. Vehicle 1 is the correct detection. | 32 |
| Vehicles 1 and 2 | 3 | Occupied. Vehicle 3 is the correct detection. | 0 |
| Vehicles 1 and 3 | 1 | Empty. Vehicle 2 is the correct rejection. | 0 |

Conservative F0 therefore has five event transitions: 902 stay clean, 149 single errors are fixed, 113 single errors are left alone, 32 double errors become triple errors, and 4 double errors stay double errors. All 149 corrections and all 32 introduced errors fall on vehicle 1. Vehicles 2 and 3 do not change a label under F0. The rule that produces this partition is the 0.90 confidence bar on the validation rates: F0 adopts a label only when vehicles 2 and 3 already agree. When they are right, vehicle 1 is corrected. When they are both wrong, vehicle 1's correct detection is erased.

Always-A changes the other two vehicles to vehicle 3. It corrects 191 single-error regions in which vehicle 3 was already right, and it turns 71 single-error regions in which vehicle 3 was the only mistake into three-vehicle mistakes. It also repairs 3 double errors and turns the other 33 into three-vehicle errors. Across labels it loses 170 correct detections: 101 on vehicle 1 and 69 on vehicle 2.

## Where a correct local detection is lost

Majority erases 35 correct detections. F0 erases 32 of them and keeps 3. All 32 are vehicle 1, with local votes `1 0 0`, at an occupied region. The 3 that F0 keeps are vehicle 3, with local votes `0 0 1`. The drawings use the exported world centers and the 7.5 m radius. The numbers inside a circle are the local votes of vehicles 1, 2, and 3. Raw lidar points and predicted boxes are not redrawn.

The 35 losses occupy five cells of the same 40-circle grid. Twenty-one are the cell at (−45 m, 0 m). Seven are (−15 m, 30 m), three are (−30 m, 15 m), and one is (−15 m, 15 m). The three detections F0 keeps are all at (30 m, 0 m).

![Both policies erase vehicle 1 at frame 481410](audit/figures/lost_detection_majority_and_f0.png)

Frame `481410`, region `grid_031`, center (−45 m, 0 m). The region is occupied. Vehicle 1 votes 1 and vehicles 2 and 3 vote 0. Majority and conservative F0 both write `0 0 0`. This cell is the one that accounts for 21 of the 32 shared losses. Its orthogonal neighbors in the zoom are locally clean or occupied with votes `1 1 0`; the lost detection is not sitting in a block of neighboring double errors.

![Majority erases vehicle 3 and F0 keeps it](audit/figures/lost_detection_majority_only.png)

Frame `481411`, region `grid_091`, center (30 m, 0 m). The region is occupied. Only vehicle 3 votes 1. Majority writes `0 0 0`. F0 rejects the 2–1 split, because the agreeing pair includes vehicle 1, and the local votes stay `0 0 1`.

![All 35 overwritten detections on the test grid](audit/figures/lost_detection_locations.png)

The gray circles are the 40 common regions, drawn once. The numbers are how many frames lose a correct detection at that cell. Red is lost by both majority and F0. The blue ring is lost by majority and kept by F0.

## Dependence

Distinct run IDs were checked as three different strings. They do not establish independent errors. The same checkpoint produced every vehicle.

On the 1,200 local error indicators, the Pearson correlations are −0.0695 for vehicles 1 and 2, −0.1089 for vehicles 1 and 3, and +0.3061 for vehicles 2 and 3. Putting all three vehicles in one dependence group makes conservative F0 accept nothing. The accepted fraction is 0, and mean error, R2, and R3 return to the local values. The gain of F0 in the table above is the gain from treating the three run IDs as separate evidence. The shared-lineage rerun removes that treatment, and the gain goes with it.

Neighboring regions are centers exactly 15 m apart on one axis. The test grid has 2,010 such pairs. The correlation below is over those pairs, so interior cells are counted once per neighbor. It is not the per-region error rate.

| Vehicle | Neighbor-pair error correlation | Pairs both wrong | Pairs expected if independent |
|---|---:|---:|---:|
| 1 | +0.2578 | 90 | 32.58 |
| 2 | −0.0505 | 2 | 8.01 |
| 3 | +0.2942 | 68 | 17.71 |

Vehicles 1 and 3 repeat mistakes on adjacent circles more often than their pair rates would imply. Vehicle 2 does not. The 36 double-error regions are not a spatial clump: 3 of them have an orthogonal neighbor that is also a double error, and only 2 of the 2,010 pairs are double errors on both ends. The repetition in the map is the same cell across frames.

That temporal repetition is strong. There are 1,160 pairs of the same region on consecutive frames. The lag-1 error correlations are 0.9768 for vehicle 1, 0.8475 for vehicle 2, and 0.9563 for vehicle 3. A circle that is wrong at frame `t` is usually wrong at frame `t+1`. An independent-frame interval treats those repeats as new evidence.

## Block bootstrap

The published intervals resample the 30 frames independently, seed `77232`, 2,000 draws. The sensitivity keeps the same seed, the same draw count, and the same policies, and replaces the independent draw with a moving block of consecutive frames. Blocks do not wrap from frame `481439` back to `481410`. A draw of length 2 uses 15 blocks, length 5 uses 6, and length 10 uses 3. Length 1 is the published frame bootstrap, and the audit required the intervals to match.

Intervals are the 2.5 and 97.5 percentiles of the paired difference from local.

| Block | Majority mean error | Majority R3 | F0 mean error | F0 R3 | Always-A mean error |
|---|---|---|---|---|---|
| 1 frame | [−0.0675, −0.0578] | [+0.0217, +0.0392] | [−0.0350, −0.0297] | [+0.0192, +0.0342] | [−0.0114, −0.0003] |
| 2 frames | [−0.0689, −0.0567] | [+0.0192, +0.0408] | [−0.0356, −0.0294] | [+0.0175, +0.0358] | [−0.0133, +0.0019] |
| 5 frames | [−0.0711, −0.0586] | [+0.0158, +0.0367] | [−0.0364, −0.0311] | [+0.0158, +0.0333] | [−0.0150, +0.0039] |
| 10 frames | [−0.0711, −0.0606] | [+0.0158, +0.0333] | [−0.0364, −0.0322] | [+0.0150, +0.0317] | [−0.0150, +0.0028] |

Weighted broadcast matches majority at every block length, and the expert override matches F0. The R2 difference is [0, 0] at every length. Majority and F0 never change which regions have two or more wrong vehicles, so a resample cannot move R2 relative to local. Their mean-error intervals stay below zero through a 10-frame block. Their R3 intervals stay above zero: the price of the lower mean error is still a rise in three-vehicle error.

Always-A is the policy the block length changes. At one frame its mean-error interval is just below zero. At two, five, and ten frames the interval includes zero. The R2 and R3 intervals stay positive at every length, about +0.05 to +0.07 for R2 and +0.075 to +0.098 for R3. Copying vehicle 3 still makes the joint error worse once consecutive frames are kept together.

## Comparison with the P1 synthetic experiment

P1 Table 3 is shock 0.18, seed `77109`, 4,000 synthetic queries and 12,000 labels. The source is `Negin_validation/P1_REPORT.md`.

| Policy | P1 mean error | P1 R2 | P1 R3 | CooperScene mean error | CooperScene R2 | CooperScene R3 |
|---|---:|---:|---:|---:|---:|---:|
| Local | 2,403/12,000 = 20.025% | 792/4,000 = 19.800% | 8/4,000 = 0.200% | 334/3,600 = 9.278% | 36/1,200 = 3.000% | 0/1,200 = 0 |
| Majority | 2,376/12,000 = 19.800% | 792/4,000 = 19.800% | 792/4,000 = 19.800% | 108/3,600 = 3.000% | 36/1,200 = 3.000% | 36/1,200 = 3.000% |
| Conservative F0 | 1,639/12,000 = 13.658% | 792/4,000 = 19.800% | 16/4,000 = 0.400% | 217/3,600 = 6.028% | 36/1,200 = 3.000% | 32/1,200 = 2.667% |
| Expert override | 165/12,000 = 1.375% | 55/4,000 = 1.375% | 55/4,000 = 1.375% | 217/3,600 = 6.028% | 36/1,200 = 3.000% | 32/1,200 = 2.667% |

The signs for majority match. Mean error falls, R2 is unchanged, and R3 rises until it equals R2. P1's majority only moved mean error from 20.025% to 19.800%, because almost every local error was already inside an R2 event. Here 262 of the 298 imperfect regions are single-vehicle mistakes, so the same vote removes most of the error and cuts the mean from 9.278% to 3.000%.

Conservative F0 also matches P1 on the two signs that the manuscript states: mean error falls, and R2 stays on the local curve. The R3 movement is larger here. P1's F0 moved R3 from 0.200% to 0.400%, which is 8 events becoming 16. There are 36 double-error regions, consisting of 35 double misses and one double false alarm. F0 accepts 32 of those 35 double misses and rejects the double false alarm, so R3 moves from 0 to 2.667%. Those 32 accepts are exactly the cases in which the two lower validation-error vehicles agree on a miss. P1's frame-bootstrap intervals for F0 minus local were mean error [−6.775, −5.950] points and R3 [+0.075, +0.350] points. The CooperScene intervals have the same signs at every block length above.

The expert result does not carry over. On the P1 draw the declared error was 1.5%, the override copied agent A on all 4,000 queries, and the error was 165/12,000 = 1.375%. The P1 rule fires only at a declared error of 0.3%, 0.6%, 1.0%, or 1.5%. At 2% or higher it matches conservative F0. The lowest validation rate in this export is 11.270%, so the override contributes no label beyond F0. Always-A, which is what the override became on the P1 draw, reaches only 312/3,600 here and raises R2 and R3 to 8.667%. Its mean-error advantage over local is small enough that a block of two or more frames lets the interval include zero.

P1 also found that an incorrect dependence grouping leaves the joint-error rate at the local value. The one-group rerun on this export is that finding on real detections: F0 accepts nothing, and the error equals local.

## Limitations

The clip is one take and 30 frames. The block bootstrap describes resampling inside that clip. It does not add a second take.

The metric is region presence inside a 7.5 m circle. It is not 3D detection mAP, and it does not ask whether the same physical vehicle was matched.

The three exports share a checkpoint. Vehicles 2 and 3 have positively correlated errors. Vehicles 1 and 3 also repeat errors on neighboring circles, and every vehicle repeats errors on the next frame. Counting the three run IDs as independent groups is an assumption. The one-group rerun shows what F0 does without that assumption.

The reliability rates are the validation region mismatches. They are not object-level F1, and they were not refit on the test split. Test region error is lower for vehicle 2 (77/1,200 = 6.417%) than for vehicle 3 (104/1,200 = 8.667%). The expert remains vehicle 3.

The 291 annotation disagreements were replayed from the validation box files, not only from the recorded gate. Restoring vehicle 1's 30 ego-dropped boxes removes none of them. The primary test file still stores the post-rule union. A secondary rescore on regions where all three kept annotations agree with that union is in the sensitivity section below. The importer rows themselves do not carry poses. The box files do, and the replay uses those poses.

The case figures are those decision regions. They are not a new rendering of the point cloud.

## What was not changed

The score stays 0.10, the radius stays 7.5 m, and the grid stays the 144 stored centers. No threshold was chosen from the test split. Detector inference was not rerun. `Octopus-main` was not edited. The manuscript was not edited.

The checked totals are in `audit/audit_summary.json`. The study tables are in `evaluation/metrics.json`, `evaluation/FINDINGS.md`, and `evaluation/stock_study/comparison.csv`.

## Final sensitivity

The three checks in this section are not the primary result. The primary table remains the 30-frame scoring above. Nothing here changes the score, the radius, the grid, or the reliability rates. Detector inference was not rerun. The script is `final_sensitivity/run_sensitivity.py`. Its write-up is `final_sensitivity/FINDINGS.md`.

### Annotation disagreement

The 291 disagreements are a property of the validation annotations, not of the detectors. The counter flags a region when the union of the three kept annotation sets hits a circle and at least one vehicle's own kept boxes miss it. A vehicle cannot produce the opposite disagreement, because the union already contains that vehicle's boxes.

The validation files `vehicle_1.jsonl`, `vehicle_2.jsonl`, `vehicle_3.jsonl`, and `summary.json` were replayed with the official rotation, the 3 m ego drop, the ±72 m window, and the 144 stored centers. The replay returned 291 disagreements on 1,047 common regions. It would have stopped on any other count. All 291 are among the 336 positive union regions. The other 45 positive regions are hit by every vehicle's kept annotations. The 711 empty regions agree. So 291/336 = 86.607% of occupied union regions are absent from at least one vehicle's own labels.

| Vehicle | Misses of a union hit | Ego exclusion | Annotation coverage |
|---|---:|---:|---:|
| 1 | 168 | 0 | 168 |
| 2 | 143 | 0 | 143 |
| 3 | 113 | 0 | 113 |

| Vehicles missing the union hit | Regions |
|---|---:|
| 1 only | 76 |
| 2 only | 28 |
| 3 only | 54 |
| 1 and 2 | 74 |
| 1 and 3 | 18 |
| 2 and 3 | 41 |

Those six rows sum to 291. Vehicle 1 is missing on 168 regions, vehicle 2 on 143, and vehicle 3 on 113.

The official rotation was applied to all 1,274 stored ego boxes across all 30 validation frames. The largest absolute residual against the stored world box is 2.132e-14 m. No box exceeds 1e-6 m, 1 mm, or 1 cm. The coordinate transform does not move a box into or out of a 7.5 m circle.

Vehicle 1 still loses 30 annotated boxes to the 3 m rule. Vehicles 2 and 3 lose none. Putting those 30 boxes back into vehicle 1's kept set and into the union removes 0 of the 291 disagreements and creates 0 new ones. Every one of the 291 is annotation coverage: the missing vehicle's raw boxes, including any box within 3 m of its lidar, do not enter the circle. The earlier bound, at most 60 regions and at least 231 remaining, was an upper limit from the lattice. The replay replaces that bound. The exact ego contribution is 0.

The 291 region-frames sit on 15 repeated centers. Five of those centers disagree on all 30 frames: (−30, −15), (−30, 0), (15, 0), (15, 15), and (30, −45). The map below overplots those repeats, so it shows the 15 centers rather than 291 separate dots.

![Validation disagreement centers](final_sensitivity/figures/gt_disagreement_map.png)

Frame 481380, `grid_042`, is one coverage disagreement. The outlined circle is occupied in the union and missed by at least one vehicle's own boxes. Vehicle 1's ego-dropped box is the cross on its lidar. It is not inside the outlined circle, which is the same fact as the zero count above.

![Coverage disagreement on frame 481380](final_sensitivity/figures/gt_annotation_coverage_example.png)

This does change how a joint miss should be read. A joint miss means all three detectors voted empty where the union is occupied. On validation, most occupied union regions are not occupied in every vehicle's own annotations. A joint miss is therefore not, by itself, evidence that all three annotation sets contained the same object. The primary scores stay on the union. The 291 disagreements were not used to choose a threshold, and they are not detector errors.

### R3 under temporal blocks

The moving-block bootstrap was run again for the change in R3. Lengths are 1, 2, 5, and 10 frames, with 2,000 draws and seed 77232. Blocks do not wrap. The interval is the 2.5 and 97.5 percentiles of policy R3 minus local R3. Length 1 matches the published frame bootstrap; the script checks that match. Local R3 is 0 on every resample, because the export has no region where all three local labels are wrong. The plotted difference is the policy's own R3 on each draw.

| Policy minus local | 1 frame | 2 frames | 5 frames | 10 frames |
|---|---|---|---|---|
| Majority | [+0.0217, +0.0392] | [+0.0192, +0.0408] | [+0.0158, +0.0367] | [+0.0158, +0.0333] |
| Weighted | [+0.0217, +0.0392] | [+0.0192, +0.0408] | [+0.0158, +0.0367] | [+0.0158, +0.0333] |
| Conservative F0 | [+0.0192, +0.0342] | [+0.0175, +0.0358] | [+0.0158, +0.0333] | [+0.0150, +0.0317] |
| Expert override | [+0.0192, +0.0342] | [+0.0175, +0.0358] | [+0.0158, +0.0333] | [+0.0150, +0.0317] |
| Always-A | [+0.0792, +0.0950] | [+0.0767, +0.0983] | [+0.0750, +0.0983] | [+0.0750, +0.0967] |

Every lower endpoint stays above zero. Longer blocks make the interval a little wider and move the lower end down, so the repeated frames make the rise less precise. They do not remove it. The rise is unfavorable for every fusion rule in the table: after the temporal dependence is kept inside the resample, R3 is still higher than local.

![R3 intervals by block length](final_sensitivity/figures/r3_block_intervals.png)

### Frame 481410 held out

Frame 481410 is the smoke-test frame, and it is inside the primary 30-frame result. Holding it out leaves 29 frames, 1,160 regions, and 3,480 labels. The same frozen labels are rescored. One of the 36 double-error regions was on that frame, and it was the illustrated loss at `grid_031`. None of the joint false alarms were on it.

| Policy | 30-frame mean error | 29-frame mean error | 30-frame R3 | 29-frame R3 | 29-frame joint misses | 29-frame corrections | 29-frame introduced errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| Local | 334/3,600 = 9.278% | 323/3,480 = 9.282% | 0/1,200 | 0/1,160 | 0 | 0 | 0 |
| Majority | 108/3,600 = 3.000% | 105/3,480 = 3.017% | 36/1,200 | 35/1,160 | 34 | 253 | 35 |
| Weighted | 108/3,600 = 3.000% | 105/3,480 = 3.017% | 36/1,200 | 35/1,160 | 34 | 253 | 35 |
| Conservative F0 | 217/3,600 = 6.028% | 210/3,480 = 6.034% | 32/1,200 | 31/1,160 | 31 | 144 | 31 |
| Expert override | 217/3,600 = 6.028% | 210/3,480 = 6.034% | 32/1,200 | 31/1,160 | 31 | 144 | 31 |
| Always-A | 312/3,600 = 8.667% | 303/3,480 = 8.707% | 104/1,200 | 101/1,160 | 98 | 190 | 170 |

Joint false alarms are unchanged: 0, 1, 1, 0, 0, and 3 for local, majority, weighted, F0, the override, and always-A. R2 moves from 36/1,200 to 35/1,160. The smoke frame was close to the take average, 11 wrong local labels out of 120, so dropping it does not improve the policies. The ordering is the same, and the R3 gap remains. This hold-out is the sensitivity result. The primary claims stay on all 30 frames.

![Thirty frames against the hold-out](final_sensitivity/figures/frame_exclusion.png)

### Unanimously annotated test regions

This rescore is secondary. The primary evaluation remains the union on all 1,200 test regions. A test region is retained only when every vehicle's kept annotations agree with that union. Empty regions are retained, because a miss by one vehicle would be a disagreement. The frozen test predictions are reused. Reliability rates, the score, the radius, and the grid are unchanged. Detector inference was not rerun.

Replaying the 144 stored centers on `test_boxes_vehicle_1.jsonl`, `test_boxes_vehicle_2.jsonl`, and `test_boxes_vehicle_3.jsonl` matched all 1,200 exported `(frame, roi)` keys. The unanimous subset retains 903 regions and 2,709 labels, and drops 297. All 297 dropped regions are positive. Of the 327 positive union regions, 30 are hit by every vehicle's kept annotations. The other 873 retained regions are empty under the union.

| Policy | Mean error | R2 | R3 | Joint false alarms | Joint misses | Corrections | Introduced errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| Local | 6/2,709 = 0.221% | 1/903 | 0/903 | 0 | 0 | 0 | 0 |
| Majority | 3/2,709 = 0.111% | 1/903 | 1/903 | 1 | 0 | 4 | 1 |
| Weighted | 3/2,709 = 0.111% | 1/903 | 1/903 | 1 | 0 | 4 | 1 |
| Conservative F0 | 4/2,709 = 0.148% | 1/903 | 0/903 | 0 | 0 | 2 | 0 |
| Expert override | 4/2,709 = 0.148% | 1/903 | 0/903 | 0 | 0 | 2 | 0 |
| Always-A | 9/2,709 = 0.332% | 3/903 | 3/903 | 3 | 0 | 2 | 5 |

The 35 double misses in the primary table sit in the 297 regions that are not unanimously annotated. The one double false alarm remains inside the unanimous subset: majority still introduces that one false alarm, and F0 still rejects it. Joint misses are 0 for every policy on this subset. That is a sensitivity result. It does not replace the union-based 1,200-region table, where those 35 double misses stay in the primary R3 counts.
