# Audit of late-fusion joint misses

A harmful query is a positive query where late fusion is wrong and at least one local detector is right. Sharing that label makes both agents wrong. A repaired joint miss is a positive query where both local detectors are wrong and late fusion is right.

The check recomputes all 35,874 trace labels with `parse_boxes` and `present` from `scripts/prepare_dmstrack_v2v4real.py`. Mismatches: 0.

## Coordinate convention

The source text is already in one KITTI camera frame. X points right, Y points down, and Z points forward. The converter reads a ground-truth Car from columns 13 and 15, which are X and Z. Height, width, length, and yaw are columns 10, 11, 12, and 16. The track id is column 1. Y, column 14, is stored and not used in the presence test.

A detection row is comma-separated. Column 1 is the class code 2, not a track id. The score is column 6. Height, width, length, X, Y, Z, and yaw are columns 7 through 13. The plots number detection boxes in file order within the frame, starting at 1, because the export has no identity field. Ground-truth labels use the track id.

The binary label is 1 when any retained center satisfies `(X-X0)^2 + (Z-Z0)^2 <= radius^2`. Retention for a detection also requires score at least the cutoff. The test does not use box overlap, height, or yaw. The drawn rectangle is the KITTI ground footprint, length along the object axis and width across it, rotated by `yaw` around Y. It is a picture of the box. It is not the test.

## Counts

Each setting has 1,993 positive queries. Across nine settings that is 17,937 positive queries.

| Radius | Score | Harmful joint misses | Repaired joint misses |
|---:|---:|---:|---:|
| 2.5 | 0.2 | 9 | 0 |
| 2.5 | 0.3 | 4 | 0 |
| 2.5 | 0.5 | 7 | 0 |
| 5.0 | 0.2 | 1 | 0 |
| 5.0 | 0.3 | 1 | 0 |
| 5.0 | 0.5 | 4 | 0 |
| 7.5 | 0.2 | 1 | 0 |
| 7.5 | 0.3 | 0 | 0 |
| 7.5 | 0.5 | 2 | 0 |

Harmful queries: 29. Repaired joint misses: 0.

The 29 harmful rows cover 16 distinct scene frames. 19 have every passing late-fusion center outside the circle. 10 have a late-fusion center inside the circle whose score is below the cutoff. None have both local detectors correct. In every harmful query the locals disagree, one is inside the circle, and late fusion's retained label is negative.

Late fusion does not repair a joint miss anywhere in the sweep. Whenever both local detectors miss a positive query, the late-fusion label is also a miss. The extra joint misses are new. They are not an exchange that fixes some double misses and creates others.

The published 7.5 m / 0.30 setting has 0 harmful queries and 0 repaired joint misses. Its joint-FN events stay the ones both local detectors already miss.

Every harmful query is listed in `harmful_joint_misses.csv`.

## Three representative cases

The three plots are chosen by rule from that list. The boundary case is the smallest distance by which a passing late-fusion center falls outside the radius, shown at score 0.30. The score case is the inside-but-rejected center at the published 0.30 cutoff. The far case is the greatest distance from the query to a passing late-fusion center, shown at the largest radius where that distance is unchanged.

### Center five millimeters outside the circle

`v2v4real_0003_0168_positive` at radius 2.5 m and score 0.30. Smallest center-test margin. The same frame fails at scores 0.2, 0.3, and 0.5; the plot uses the paper cutoff 0.3.

Truth is 1. Ego is 1, the partner is 0, and late fusion is 0. The correct local detector is ego. The query center is (21.830, 9.500) in KITTI X and Z.

- Ego 1 at (21.548, 9.388), score 0.736, center distance 0.303 m, center inside, footprint meets the circle.
- Ground truth 45 at (21.830, 9.500), no score, center distance 0.000 m, center inside, footprint meets the circle.
- Late fusion 1 at (19.328, 9.607), score 0.800, center distance 2.505 m, center outside, footprint meets the circle.
- Partner 1 at (19.328, 9.607), score 0.800, center distance 2.505 m, center outside, footprint meets the circle.

Plot: `boundary.png`.

### Center inside the circle, score below the cutoff

`v2v4real_0006_0179_positive` at radius 5.0 m and score 0.30. A late-fusion center lies inside the circle, but its score is below the cutoff. This is the published 0.30 cutoff.

Truth is 1. Ego is 1, the partner is 0, and late fusion is 0. The correct local detector is ego. The query center is (17.589, 34.735) in KITTI X and Z.

- Ego 5 at (13.114, 33.763), score 0.309, center distance 4.580 m, center inside, footprint meets the circle.
- Ground truth 122 at (17.589, 34.735), no score, center distance 0.000 m, center inside, footprint meets the circle.
- Ground truth 115 at (11.725, 33.749), no score, center distance 5.947 m, center outside, footprint meets the circle.
- Ground truth 117 at (11.229, 37.399), no score, center distance 6.896 m, center outside, footprint meets the circle.
- Late fusion 8 at (17.450, 34.980), score 0.291, center distance 0.281 m, center inside, footprint meets the circle.
- Late fusion 6 at (11.854, 33.905), score 0.631, center distance 5.795 m, center outside, footprint meets the circle.
- Partner 7 at (17.450, 34.980), score 0.291, center distance 0.281 m, center inside, footprint meets the circle.
- Partner 5 at (11.854, 33.905), score 0.631, center distance 5.795 m, center outside, footprint meets the circle.

Plot: `score_cutoff.png`.

### Nearest passing late-fusion center is far outside

`v2v4real_0005_0258_positive` at radius 7.5 m and score 0.20. Largest distance from the query to the nearest late-fusion box that passes the score cutoff. The largest radius is kept when that distance is tied.

Truth is 1. Ego is 0, the partner is 1, and late fusion is 0. The correct local detector is partner. The query center is (63.651, -17.648) in KITTI X and Z.

- Ground truth 213 at (63.651, -17.648), no score, center distance 0.000 m, center inside, footprint meets the circle.
- Late fusion 18 at (71.355, -0.317), score 0.546, center distance 18.967 m, center outside, footprint misses the circle.
- Partner 15 at (64.236, -18.267), score 0.208, center distance 0.851 m, center inside, footprint meets the circle.

Plot: `far_detection.png`.

In the boundary plot, the late-fusion footprint crosses the circle while its center does not. The label follows the center. In the score plot, the dashed box is inside the circle and is ignored because its score is below 0.30. In the far plot, the passing late-fusion box is a different car, well outside the query, so widening the radius from 2.5 m to 7.5 m does not bring its center in.

