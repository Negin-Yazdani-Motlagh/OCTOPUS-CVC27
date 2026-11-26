# Spatial sensitivity of the nine-sequence queries

The queries come from the unmodified `scripts/prepare_dmstrack_v2v4real.py`. Each of the nine settings changes only `--radius` and `--threshold`. The cached DMSTrack text at commit `d3b9949499c8e68ea33060873bd1cb95b6d4d323` is the input. The 7.5 m / 0.30 trace matches the earlier regeneration event for event.

## How a query is chosen

The files are already in one shared KITTI camera frame. X and Z are the ground plane. Y is height and is not used. A ground-truth Car uses track id column 1, class column 2, and center columns 13 and 15. A detection uses class code 2, score column 6, and center columns 10 and 12. No new coordinate transform is applied.

A binary label is 1 when any retained Car center lies within the radius of the query center, including the boundary. It is 0 otherwise. The label does not identify a track, count the cars, or measure 3D box overlap. Several cars in one circle still produce one presence label.

The balanced task uses ground truth only to place the regions. On each frame it anchors the positive query on the car at index `frame mod number of cars`. It then tries the offsets (18, 0), (−18, 0), (0, 18), (0, −18), (25, 0), (−25, 0), (0, 25), (0, −25), and (35, 15), and keeps the first offset whose circle contains no ground-truth center. Score does not move either center. Ground truth is never filtered by score. A detection center is kept only when its score is at least the cutoff, so the same region can change its predicted label when the cutoff changes.

The fixed grid is separate: 12 centers at X in {−40, −20, 0, 20} and Z in {−10, 15, 40}, on every frame. Its locations do not depend on radius or score. Its labels do.

## What changes across the nine settings

Every radius keeps all 1,993 frames. No frame fails to find a negative offset. Each emitted frame still contributes one positive and one negative query, so every balanced setting has 3,986 queries and a 1,993 / 1,993 class split.

| Radius | Positive centers moved vs 7.5 m | Negative centers moved vs 7.5 m | Positive regions with 2 or more GT cars | Max GT cars in one positive region |
|---:|---:|---:|---:|---:|
| 2.5 | 0 / 1993 | 525 / 1993 | 16 / 1993 | 2 |
| 5.0 | 0 / 1993 | 280 / 1993 | 654 / 1993 | 5 |
| 7.5 | 0 / 1993 | 0 / 1993 | 1020 / 1993 | 7 |

The positive anchor never moves. At 2.5 m, 1977 of 1993 positive regions contain one ground-truth car. At 7.5 m, 1020 of 1993 positive regions contain two or more cars. The binary label is still only presence.

Negative centers do move. A smaller circle lets a nearer offset qualify.

| Radius | Most common negative offset | Frames | Second offset | Frames |
|---:|---|---:|---|---:|
| 2.5 | (18, 0) | 1772 | (-18, 0) | 199 |
| 5.0 | (18, 0) | 1527 | (-18, 0) | 355 |
| 7.5 | (18, 0) | 1326 | (-18, 0) | 412 |

Score changes which detection centers are allowed to vote. It does not change truth or query centers. Label flips below are counts of queries whose binary prediction differs from the 0.30 cutoff at the same radius.

| Score | Ego boxes | Partner boxes | Late-fusion boxes | CoBEVT boxes |
|---:|---:|---:|---:|---:|
| 0.2 | 29837 | 30209 | 42718 | 33848 |
| 0.3 | 21854 | 23617 | 32363 | 26913 |
| 0.5 | 12783 | 15378 | 20774 | 15536 |

| Radius | Score | Ego flips vs 0.30 | Partner flips | Late-fusion flips |
|---:|---:|---:|---:|---:|
| 2.5 | 0.2 | 169 / 3986 | 134 / 3986 | 109 / 3986 |
| 2.5 | 0.5 | 411 / 3986 | 376 / 3986 | 465 / 3986 |
| 5.0 | 0.2 | 184 / 3986 | 129 / 3986 | 122 / 3986 |
| 5.0 | 0.5 | 440 / 3986 | 370 / 3986 | 422 / 3986 |
| 7.5 | 0.2 | 205 / 3986 | 148 / 3986 | 157 / 3986 |
| 7.5 | 0.5 | 414 / 3986 | 337 / 3986 | 371 / 3986 |

## Balanced policies

Local keeps both detector labels. Late fusion assigns its label to both agents, so its mean error equals its R2. The disagreement gate uses late fusion only when the local labels differ. OR uses 1 when either local label is 1. Mean error uses both agent labels. R2 uses queries. Joint false negatives use the 1,993 positive queries, and joint false positives use the 1,993 negative queries.

### Radius 2.5 m, score 0.2

| Policy | Mean error | Joint FN | Joint FP | R2 |
|---|---:|---:|---:|---:|
| Local | 1211/7972 = 15.19% | 90/1993 = 4.52% | 4/1993 = 0.20% | 94/3986 = 2.36% |
| Late Fusion | 276/7972 = 3.46% | 99/1993 = 4.97% | 39/1993 = 1.96% | 138/3986 = 3.46% |
| Disagreement Gate | 276/7972 = 3.46% | 99/1993 = 4.97% | 39/1993 = 1.96% | 138/3986 = 3.46% |
| OR | 282/7972 = 3.54% | 90/1993 = 4.52% | 51/1993 = 2.56% | 141/3986 = 3.54% |

### Radius 2.5 m, score 0.3

| Policy | Mean error | Joint FN | Joint FP | R2 |
|---|---:|---:|---:|---:|
| Local | 1474/7972 = 18.49% | 189/1993 = 9.48% | 1/1993 = 0.05% | 190/3986 = 4.77% |
| Late Fusion | 434/7972 = 5.44% | 193/1993 = 9.68% | 24/1993 = 1.20% | 217/3986 = 5.44% |
| Disagreement Gate | 434/7972 = 5.44% | 193/1993 = 9.68% | 24/1993 = 1.20% | 217/3986 = 5.44% |
| OR | 446/7972 = 5.59% | 189/1993 = 9.48% | 34/1993 = 1.71% | 223/3986 = 5.59% |

### Radius 2.5 m, score 0.5

| Policy | Mean error | Joint FN | Joint FP | R2 |
|---|---:|---:|---:|---:|
| Local | 2213/7972 = 27.76% | 636/1993 = 31.91% | 0/1993 = 0.00% | 636/3986 = 15.96% |
| Late Fusion | 1304/7972 = 16.36% | 643/1993 = 32.26% | 9/1993 = 0.45% | 652/3986 = 16.36% |
| Disagreement Gate | 1304/7972 = 16.36% | 643/1993 = 32.26% | 9/1993 = 0.45% | 652/3986 = 16.36% |
| OR | 1294/7972 = 16.23% | 636/1993 = 31.91% | 11/1993 = 0.55% | 647/3986 = 16.23% |

### Radius 5.0 m, score 0.2

| Policy | Mean error | Joint FN | Joint FP | R2 |
|---|---:|---:|---:|---:|
| Local | 1065/7972 = 13.36% | 54/1993 = 2.71% | 27/1993 = 1.35% | 81/3986 = 2.03% |
| Late Fusion | 334/7972 = 4.19% | 55/1993 = 2.76% | 112/1993 = 5.62% | 167/3986 = 4.19% |
| Disagreement Gate | 334/7972 = 4.19% | 55/1993 = 2.76% | 112/1993 = 5.62% | 167/3986 = 4.19% |
| OR | 342/7972 = 4.29% | 54/1993 = 2.71% | 117/1993 = 5.87% | 171/3986 = 4.29% |

### Radius 5.0 m, score 0.3

| Policy | Mean error | Joint FN | Joint FP | R2 |
|---|---:|---:|---:|---:|
| Local | 1254/7972 = 15.73% | 132/1993 = 6.62% | 13/1993 = 0.65% | 145/3986 = 3.64% |
| Late Fusion | 402/7972 = 5.04% | 133/1993 = 6.67% | 68/1993 = 3.41% | 201/3986 = 5.04% |
| Disagreement Gate | 402/7972 = 5.04% | 133/1993 = 6.67% | 68/1993 = 3.41% | 201/3986 = 5.04% |
| OR | 402/7972 = 5.04% | 132/1993 = 6.62% | 69/1993 = 3.46% | 201/3986 = 5.04% |

### Radius 5.0 m, score 0.5

| Policy | Mean error | Joint FN | Joint FP | R2 |
|---|---:|---:|---:|---:|
| Local | 1962/7972 = 24.61% | 510/1993 = 25.59% | 3/1993 = 0.15% | 513/3986 = 12.87% |
| Late Fusion | 1082/7972 = 13.57% | 514/1993 = 25.79% | 27/1993 = 1.35% | 541/3986 = 13.57% |
| Disagreement Gate | 1082/7972 = 13.57% | 514/1993 = 25.79% | 27/1993 = 1.35% | 541/3986 = 13.57% |
| OR | 1076/7972 = 13.50% | 510/1993 = 25.59% | 28/1993 = 1.40% | 538/3986 = 13.50% |

### Radius 7.5 m, score 0.2

| Policy | Mean error | Joint FN | Joint FP | R2 |
|---|---:|---:|---:|---:|
| Local | 1076/7972 = 13.50% | 38/1993 = 1.91% | 40/1993 = 2.01% | 78/3986 = 1.96% |
| Late Fusion | 494/7972 = 6.20% | 39/1993 = 1.96% | 208/1993 = 10.44% | 247/3986 = 6.20% |
| Disagreement Gate | 492/7972 = 6.17% | 39/1993 = 1.96% | 207/1993 = 10.39% | 246/3986 = 6.17% |
| OR | 518/7972 = 6.50% | 38/1993 = 1.91% | 221/1993 = 11.09% | 259/3986 = 6.50% |

### Radius 7.5 m, score 0.3

| Policy | Mean error | Joint FN | Joint FP | R2 |
|---|---:|---:|---:|---:|
| Local | 1151/7972 = 14.44% | 91/1993 = 4.57% | 14/1993 = 0.70% | 105/3986 = 2.63% |
| Late Fusion | 388/7972 = 4.87% | 91/1993 = 4.57% | 103/1993 = 5.17% | 194/3986 = 4.87% |
| Disagreement Gate | 384/7972 = 4.82% | 91/1993 = 4.57% | 101/1993 = 5.07% | 192/3986 = 4.82% |
| OR | 398/7972 = 4.99% | 91/1993 = 4.57% | 108/1993 = 5.42% | 199/3986 = 4.99% |

### Radius 7.5 m, score 0.5

| Policy | Mean error | Joint FN | Joint FP | R2 |
|---|---:|---:|---:|---:|
| Local | 1736/7972 = 21.78% | 390/1993 = 19.57% | 3/1993 = 0.15% | 393/3986 = 9.86% |
| Late Fusion | 850/7972 = 10.66% | 392/1993 = 19.67% | 33/1993 = 1.66% | 425/3986 = 10.66% |
| Disagreement Gate | 850/7972 = 10.66% | 392/1993 = 19.67% | 33/1993 = 1.66% | 425/3986 = 10.66% |
| OR | 852/7972 = 10.69% | 390/1993 = 19.57% | 36/1993 = 1.81% | 426/3986 = 10.69% |

## Do the earlier findings hold?

The earlier balanced result, at 7.5 m and score 0.30, is unchanged: local mean error 1,151/7,972 = 14.44%, late fusion 388/7,972 = 4.87%, local R2 105/3,986 = 2.63%, late-fusion R2 194/3,986 = 4.87%, joint false negatives 91/1,993 for every policy, and joint false positives 14, 103, 101, and 108. Sequence 0007 remains 221 frames, with joint false negatives 4 and joint false positives 0, 12, 10, and 10. The gate still matches OR on that sequence.

| Radius | Score | Late mean error lower | Late R2 higher | Same joint-FN events | Gate/OR queries that differ | Gate wrong on those queries | Sequences with equal gate and OR | Sequences with higher late-fusion R2 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.5 | 0.2 | True | True | False | 21 | 9 | 6 / 9 | 7 higher, 2 equal, 0 lower |
| 2.5 | 0.3 | True | True | False | 14 | 4 | 6 / 9 | 6 higher, 3 equal, 0 lower |
| 2.5 | 0.5 | True | True | False | 9 | 7 | 5 / 9 | 6 higher, 3 equal, 0 lower |
| 5.0 | 0.2 | True | True | False | 6 | 1 | 5 / 9 | 9 higher, 0 equal, 0 lower |
| 5.0 | 0.3 | True | True | False | 2 | 1 | 9 / 9 | 6 higher, 3 equal, 0 lower |
| 5.0 | 0.5 | True | True | False | 5 | 4 | 7 / 9 | 6 higher, 3 equal, 0 lower |
| 7.5 | 0.2 | True | True | False | 15 | 1 | 3 / 9 | 9 higher, 0 equal, 0 lower |
| 7.5 | 0.3 | True | True | True | 7 | 0 | 5 / 9 | 8 higher, 1 equal, 0 lower |
| 7.5 | 0.5 | True | True | False | 5 | 2 | 7 / 9 | 8 higher, 1 equal, 0 lower |

Late fusion has a lower pooled mean error than local in 9 of 9 settings. Late fusion has a higher pooled R2 in 9 of 9. The four policies miss the same positive queries in 1 of 9. The gate and OR differ only on negative queries, with the gate label true on every differing query, in 1 of 9.

At 7.5 m and score 0.30, the gate matches OR on 5 of 9 sequences, and late-fusion R2 is higher on 8, equal on 1, and lower on 0. Across the sweep, sequences where gate equals OR take the values [3, 5, 6, 7, 9]. The higher/equal/lower late-fusion R2 sequence counts take the values [(6, 3, 0), (7, 2, 0), (8, 1, 0), (9, 0, 0)].

Identical joint-FN events, and a gate that is right on every disagreement with OR, hold only at 7.5 m and score 0.30. In the other eight settings, late fusion is negative on some positive queries where the two local labels disagree. The gate adopts that negative label, so both agents miss. OR keeps the local positive label, so its joint-FN count stays equal to local. The gate is wrong on exactly those positive disagreements. On the remaining disagreements, which are negative queries, the gate stays correct and OR adds a false alarm.

That extra miss can outweigh OR's extra false alarms. At 2.5 m and score 0.50, OR mean error is 1,294/7,972 = 16.23%, while the gate and late fusion are 1,304/7,972 = 16.36%. At 5.0 m and score 0.50, OR is 1,076/7,972 = 13.50% and the gate is 1,082/7,972 = 13.57%. The published ordering, gate ahead of OR, is not true at those two settings. No sequence in this sweep has a late-fusion R2 below its local R2. Some sequences are tied.

## Fixed grid

The grid has 12 regions on each of 1,993 frames, so every setting has 23,916 queries. Positive prevalence changes with radius because a larger circle covers more cars. At 7.5 m and score 0.30 the converter matches the published grid: 4,052 positive queries, 1,020 ego errors, 1,718 partner errors, 291 separate joint errors, and 1,078 late-fusion errors.

On this grid, sharing does not improve both vehicles. At 7.5 m and 0.30, ego is wrong on 1,020/23,916 = 4.26% of queries and late fusion is wrong on 1,078/23,916 = 4.51%. The partner is wrong on 1,718/23,916 = 7.18%. Local R2 is 291/23,916 = 1.22%, and late-fusion R2 is 4.51%. The balanced-task statement that late fusion lowers every vehicle's error does not hold on the grid.

| Radius | Score | Positives | Local mean | Late fusion mean / R2 | Gate mean / R2 | OR mean / R2 | Local R2 | Joint FN local | Joint FP local | Joint FP late |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.5 | 0.2 | 240/23916 | 376/47832 = 0.79% | 188/23916 = 0.79% | 188/23916 = 0.79% | 203/23916 = 0.85% | 39/23916 = 0.16% | 26/240 | 13/23676 | 157/23676 |
| 2.5 | 0.3 | 240/23916 | 294/47832 = 0.61% | 109/23916 = 0.46% | 108/23916 = 0.45% | 118/23916 = 0.49% | 40/23916 = 0.17% | 35/240 | 5/23676 | 70/23676 |
| 2.5 | 0.5 | 240/23916 | 335/47832 = 0.70% | 110/23916 = 0.46% | 110/23916 = 0.46% | 115/23916 = 0.48% | 85/23916 = 0.36% | 83/240 | 2/23676 | 26/23676 |
| 5.0 | 0.2 | 1786/23916 | 1591/47832 = 3.33% | 906/23916 = 3.79% | 905/23916 = 3.78% | 1008/23916 = 4.21% | 130/23916 = 0.54% | 59/1786 | 71/22130 | 815/22130 |
| 5.0 | 0.3 | 1786/23916 | 1375/47832 = 2.87% | 618/23916 = 2.58% | 616/23916 = 2.58% | 621/23916 = 2.60% | 148/23916 = 0.62% | 129/1786 | 19/22130 | 461/22130 |
| 5.0 | 0.5 | 1786/23916 | 2469/47832 = 5.16% | 903/23916 = 3.78% | 906/23916 = 3.79% | 903/23916 = 3.78% | 676/23916 = 2.83% | 673/1786 | 3/22130 | 212/22130 |
| 7.5 | 0.2 | 4052/23916 | 3045/47832 = 6.37% | 1691/23916 = 7.07% | 1689/23916 = 7.06% | 1718/23916 = 7.18% | 450/23916 = 1.88% | 105/4052 | 345/19864 | 1544/19864 |
| 7.5 | 0.3 | 4052/23916 | 2738/47832 = 5.72% | 1078/23916 = 4.51% | 1076/23916 = 4.50% | 1083/23916 = 4.53% | 291/23916 = 1.22% | 232/4052 | 59/19864 | 806/19864 |
| 7.5 | 0.5 | 4052/23916 | 4346/47832 = 9.09% | 1567/23916 = 6.55% | 1576/23916 = 6.59% | 1569/23916 = 6.56% | 1317/23916 = 5.51% | 1313/4052 | 4/19864 | 229/19864 |

## Examples at the published setting

The figure `topdown_examples.png` uses 7.5 m and score 0.30. Circles are query regions. Points are box centers within 45 m of the query. Ground-truth labels are track ids.

- rescued_miss: `v2v4real_0007_0000_positive`, truth 1, ego 1, partner 0, late fusion 1. GT track ids inside the circle: 1.
- shared_false_alarm: `v2v4real_0007_0005_negative`, truth 0, ego 1, partner 0, late fusion 1. GT track ids inside the circle: none.
- shared_miss: `v2v4real_0007_0035_positive`, truth 1, ego 0, partner 0, late fusion 0. GT track ids inside the circle: 1.


The shared-miss example is a positive query that both local detectors and late fusion miss. At this setting the four policies miss the same positive queries, so there is no positive query where late fusion is wrong while either local detector is right. Late fusion introduces joint errors on negative queries, which is the shared false alarm.

These plots are presence checks in the X–Z plane. They are not 3D IoU, average precision, or a sample of natural hazard frequency. The balanced task forces one positive and one negative query per frame, so its error rates are not the rates on the fixed grid.

