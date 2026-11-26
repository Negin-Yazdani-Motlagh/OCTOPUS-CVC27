# Validation recommendation

Date: 25 November 2026. Job on `a1117u29n01`. Split: `validate` only, timestamps 481380–481409, vehicles 1, 2, and 3. Thirty frames each. Failures: 0. Agent 0 was not used. The test split was not used.

Ground-truth instances: 437 for vehicle 1, 396 for vehicle 2, 441 for vehicle 3, 1274 in total. Each forward returned 200 boxes because that is the head's proposal limit. Only boxes at or above a score cutoff enter the counts below.

Matching is one-to-one in the ego lidar frame. World centers match the official YAML boxes to 2.1e-14 m, so the pose inverse is the official transform.

## Score cutoff: 0.1

Use **0.1**. It has the highest pooled F1 at BEV IoU 0.50 among the four cutoffs fixed before the run (0.05, 0.1, 0.3, 0.5). The next cutoff, 0.3, is 0.012 F1 lower, outside the 0.01 tie band, so the higher cutoff is not substituted. The same ranking holds at BEV IoU 0.70, which was not used to make the choice.

Pooled, one-to-one, IoU 0.50:

| Score | Precision | Recall | F1 | False positives | Misses |
|---|---|---|---|---|---|
| 0.05 | 0.889 | 0.984 | 0.934 | 157 | 20 |
| **0.1** | **0.943** | **0.980** | **0.962** | **75** | **25** |
| 0.3 | 0.984 | 0.918 | 0.950 | 19 | 105 |
| 0.5 | 0.998 | 0.786 | 0.879 | 2 | 273 |

At the recommended cutoff and IoU 0.50, by vehicle:

| Vehicle | Precision | Recall | F1 | False positives | Misses |
|---|---|---|---|---|---|
| 1 | 0.968 | 0.970 | 0.969 | 14 | 13 |
| 2 | 0.894 | 0.975 | 0.932 | 46 | 10 |
| 3 | 0.967 | 0.995 | 0.981 | 15 | 2 |

Vehicle 2 produces most of the remaining false positives. Vehicle 3 is the strongest of the three. At IoU 0.70 and score 0.1, pooled precision is 0.877, recall is 0.911, and F1 is 0.894.

0.3 is the high-precision alternative: 19 false positives and 105 misses. It is not the cutoff selected by the predeclared rule. Do not refit this choice on the test split.

## World grid

| Item | Value |
|---|---|
| Frame | `cooperscene_global_xy_m` |
| Radius | 7.5 m |
| Lattice spacing | 15 m |
| Origin | (−75 m, −105 m) |
| Circles | 144 |
| What a positive label means | Any retained vehicle center lies inside the circle |

The radius is the 7.5 m radius already named for this study. It was not adjusted to these detections. The lattice is aligned to multiples of 15 m and covers the validation ground-truth centers. The run flagged that vehicles in the same frame often stand closer than 15 m, so one circle can contain more than one vehicle. The label is presence, not identity, and it is not a 3D IoU.

## Runtime

Steady-state inference is about 0.053–0.058 s per frame after the point cloud is a `.bin`. Vehicle 1's first frame took 0.389 s. Peak allocated GPU memory during inference was 598 MiB. Peak reserved memory was 932 MiB. The B200 was far from full.

Per-box files remain on the cluster at `/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/validation_inference/` (`vehicle_1.jsonl`, `vehicle_2.jsonl`, `vehicle_3.jsonl`, `metrics.csv`, `summary.json`).
