# Frozen CooperScene protocol

Frozen from the validation run on 25 November 2026, before any test frame is read.

| Choice | Value | Source |
|---|---|---|
| Score | 0.10 | Highest pooled object F1 was used only to choose this cutoff. It is not the reliability number. |
| Radius | 7.5 m | Named in the study plan. Not refit. |
| Spacing | 15 m | One diameter. Not refit. |
| Origin | (−75 m, −105 m) | Validation grid. |
| Circles | 144 centers stored in the validation `summary.json` | Used as stored. Not redrawn from test boxes. |
| Coordinate frame | `cooperscene_global_xy_m` | Importer requirement. |

A region is positive when any kept vehicle-center lies inside the circle. That is presence, not identity and not 3D IoU.

## Checks that must pass before test inference

The test loop does not start unless all of these hold on the validation export.

1. Common coverage. A circle is eligible on a frame only when its center falls inside the published detector window, x and y within ±72 m, for every vehicle after the official lidar rotation. Every validation frame must have at least one eligible circle. The same rule, with the same centers, is applied to test poses. Test boxes are not used to add or remove circles.
2. Ego vehicles. A box whose horizontal center is within 3 m of the annotating vehicle's lidar is that vehicle itself and is dropped from both its ground truth and its predictions. The same box remains if another vehicle annotated it. The check fails if this rule would drop more than 10 percent of a vehicle's annotated boxes, or more than 10 percent of its boxes at score 0.10 or higher.
3. One ground-truth label. The exported truth is the union of the three vehicles' remaining boxes. A single vehicle's own annotations are not substituted when they disagree with that union. The disagreement rate is reported. It is not used to change the rule.

## Region-level reliability

For each vehicle, the validation error probability is the fraction of eligible regions where its binary decision differs from the shared truth. Object-level precision, recall, and F1 are not copied into this number.

The OCTOPUS importer accepts a fitted-error status only when the fit was made on the train split. This study was told to use validation only, so the manifest records the measured rates under `unfitted_assumption` and states that fact. It does not claim a train fit.

Run identifiers, all different, all using the same published checkpoint:

- `bevfusion_single_lidar_test_vehicle1`
- `bevfusion_single_lidar_test_vehicle2`
- `bevfusion_single_lidar_test_vehicle3`

Agent 0 is not included. The model is not trained. `Octopus-main` is not edited.
