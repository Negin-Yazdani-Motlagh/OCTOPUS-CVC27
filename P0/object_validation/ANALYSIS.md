# Object-level check of the 29 harmful region queries

This is an additional check. The region labels in `spatial_audit/harmful_joint_misses.csv` are unchanged. A query remains harmful at an IoU threshold only when late fusion is not matched to the anchor car and at least one local detector is.

## Box convention

The text files are the DMSTrack export at commit `d3b9949499c8e68ea33060873bd1cb95b6d4d323`. A detection row is the AB3DMOT tracking input written by `Object_3D.convert_to_trk_input_str`: frame, class code, four image-box values, score, height, width, length, camera x, y, z, yaw, alpha. Class code 2 is Car. The ground-truth tracking row is frame, track id, type, truncation, occlusion, alpha, four image-box values, height, width, length, camera x, y, z, yaw.

The ground rectangle follows `Box3D.box2corners3d_camcoord`. Before yaw, length lies along camera X and width along camera Z. Yaw is `roty` from `kitti_oxts.py`: the matrix `[[cos, 0, sin], [0, 1, 0], [-sin, 0, cos]]`. The bird's-eye-view polygon is that bottom rectangle in X and Z, the same projection `iou3d` uses. Height and camera Y are not part of this overlap.

Matching follows the one-frame rule in OpenCOOD `caluclate_tp_fp`: detections that meet the original score cutoff are considered from highest score to lowest, and each takes the still-unmatched ground-truth car with the largest overlap when that overlap is at least 0.50 or, in a separate pass, 0.70. Ego, the partner, and late fusion are matched separately.

The geometric tests in `test_bev_iou.py` passed (11 tests): identical boxes, a half-turn of the same box, separated boxes, an axis-aligned half overlap of 1/3, a contained box, a quarter-turn overlap of 1/3, and the one-to-one score and overlap rules.

## Side-by-side result

Region columns are the original center-in-circle labels. Object columns are 1 when the anchor car receives a detection at that IoU threshold.

| event | radius | score | region ego, partner, late | object 0.50 ego, partner, late | object 0.70 ego, partner, late | 0.50 | 0.70 |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| v2v4real_0003_0168_positive | 2.5 | 0.2 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0003_0176_positive | 2.5 | 0.2 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0003_0188_positive | 2.5 | 0.2 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0004_0085_positive | 2.5 | 0.2 | 0, 1, 0 | 0, 1, 0 | 0, 1, 0 | remains_harmful | remains_harmful |
| v2v4real_0004_0115_positive | 2.5 | 0.2 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0005_0018_positive | 2.5 | 0.2 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0005_0258_positive | 2.5 | 0.2 | 0, 1, 0 | 0, 0, 0 | 0, 0, 0 | neither_local_matches_anchor | neither_local_matches_anchor |
| v2v4real_0006_0009_positive | 2.5 | 0.2 | 0, 1, 0 | 0, 0, 0 | 0, 0, 0 | neither_local_matches_anchor | neither_local_matches_anchor |
| v2v4real_0006_0125_positive | 2.5 | 0.2 | 0, 1, 0 | 0, 1, 0 | 0, 0, 0 | remains_harmful | neither_local_matches_anchor |
| v2v4real_0003_0168_positive | 2.5 | 0.3 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0003_0176_positive | 2.5 | 0.3 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0003_0188_positive | 2.5 | 0.3 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0005_0018_positive | 2.5 | 0.3 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0003_0168_positive | 2.5 | 0.5 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0003_0176_positive | 2.5 | 0.5 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0003_0188_positive | 2.5 | 0.5 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0005_0018_positive | 2.5 | 0.5 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0006_0215_positive | 2.5 | 0.5 | 1, 0, 0 | 1, 0, 0 | 1, 0, 0 | remains_harmful | remains_harmful |
| v2v4real_0007_0069_positive | 2.5 | 0.5 | 0, 1, 0 | 0, 1, 0 | 0, 1, 0 | remains_harmful | remains_harmful |
| v2v4real_0007_0141_positive | 2.5 | 0.5 | 0, 1, 0 | 0, 1, 0 | 0, 1, 0 | remains_harmful | remains_harmful |
| v2v4real_0005_0258_positive | 5.0 | 0.2 | 0, 1, 0 | 0, 0, 0 | 0, 0, 0 | neither_local_matches_anchor | neither_local_matches_anchor |
| v2v4real_0006_0179_positive | 5.0 | 0.3 | 1, 0, 0 | 0, 0, 0 | 0, 0, 0 | neither_local_matches_anchor | neither_local_matches_anchor |
| v2v4real_0006_0013_positive | 5.0 | 0.5 | 1, 0, 0 | 0, 0, 0 | 0, 0, 0 | neither_local_matches_anchor | neither_local_matches_anchor |
| v2v4real_0007_0069_positive | 5.0 | 0.5 | 0, 1, 0 | 0, 1, 0 | 0, 1, 0 | remains_harmful | remains_harmful |
| v2v4real_0007_0141_positive | 5.0 | 0.5 | 0, 1, 0 | 0, 1, 0 | 0, 1, 0 | remains_harmful | remains_harmful |
| v2v4real_0008_0133_positive | 5.0 | 0.5 | 0, 1, 0 | 0, 0, 0 | 0, 0, 0 | neither_local_matches_anchor | neither_local_matches_anchor |
| v2v4real_0005_0258_positive | 7.5 | 0.2 | 0, 1, 0 | 0, 0, 0 | 0, 0, 0 | neither_local_matches_anchor | neither_local_matches_anchor |
| v2v4real_0003_0056_positive | 7.5 | 0.5 | 1, 0, 0 | 0, 0, 0 | 0, 0, 0 | neither_local_matches_anchor | neither_local_matches_anchor |
| v2v4real_0007_0069_positive | 7.5 | 0.5 | 0, 1, 0 | 0, 1, 0 | 0, 1, 0 | remains_harmful | remains_harmful |

Of the 29 query-setting rows, 21 remain harmful at IoU 0.50 and 20 remain harmful at IoU 0.70.

## Why the others do not

### IoU 0.50

- `v2v4real_0005_0258_positive` at score 0.2 and radius 2.5, 5.0, 7.5 m. Partner box 15 scores 0.208 and its center is 0.851 m from anchor track 213. Their overlap is 0.400, below 0.50. Late fusion's best eligible overlap is 0.000.
- `v2v4real_0006_0009_positive` at score 0.2 and radius 2.5 m. Partner box 9 scores 0.266 and its center is 1.493 m from anchor track 13. Their overlap is 0.437, below 0.50. Late fusion's best eligible overlap is 0.394.
- `v2v4real_0006_0179_positive` at score 0.3 and radius 5.0 m. Ego box 5 scores 0.309 and its center is 4.580 m from anchor track 122, but the two boxes do not overlap. The strongest box below the score cutoff is partner box 7, score 0.291, overlap 0.650 with the anchor.
- `v2v4real_0006_0013_positive` at score 0.5 and radius 5.0 m. Ego box 5 scores 0.632 and its center is 4.125 m from anchor track 4, but the two boxes do not overlap. At IoU 0.50 that detection is matched to track 3 with overlap 0.682. The strongest box below the score cutoff is late box 10, score 0.360, overlap 0.673 with the anchor.
- `v2v4real_0008_0133_positive` at score 0.5 and radius 5.0 m. Partner box 16 scores 0.506 and its center is 4.083 m from anchor track 7, but the two boxes do not overlap. At IoU 0.50 that detection is matched to track 110 with overlap 0.867. The strongest box below the score cutoff is partner box 20, score 0.284, overlap 0.701 with the anchor.
- `v2v4real_0003_0056_positive` at score 0.5 and radius 7.5 m. Ego box 6 scores 0.501 and its center is 6.312 m from anchor track 22, but the two boxes do not overlap. At IoU 0.50 that detection is matched to track 18 with overlap 0.811.

### IoU 0.70

Every row that misses 0.50 also misses 0.70. One further row falls between the two thresholds.

- `v2v4real_0006_0125_positive` at score 0.2 and radius 2.5 m. Partner box 7 scores 0.298 and its center is 0.618 m from anchor track 13. Their overlap is 0.632, below 0.70. Late fusion's best eligible overlap is 0.378.

Late fusion does not match the anchor in any of the 29 rows. Its largest eligible overlap with an anchor is 0.394. The local matches that remain harmful at 0.50 all have overlap at least 0.632. On the boundary example `v2v4real_0003_0168_positive` at score 0.3, late fusion's best eligible overlap with anchor track 45 is 0.269, while ego's is 0.790.

One-to-one matching did not give any of these anchors to a different car. When an eligible detection cleared the threshold against the anchor, that detection was still available.

Counts and the matched box ids are in `harmful_object_matches.csv`.
