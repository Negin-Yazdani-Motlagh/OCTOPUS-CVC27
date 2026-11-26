# Final sensitivity checks

These three checks are sensitivity analyses. The primary result remains the 30-frame table in `../P2_REPORT.md`. No threshold, radius, or grid value was changed. Detector inference was not rerun. `Octopus-main` was not edited.

## 1. Ground-truth consistency

A validation region disagrees when at least one vehicle's own kept annotations miss a circle that the union of the three kept annotation sets hits. The union is the shared truth. A vehicle cannot hit a circle the union misses, because the union contains that vehicle's kept boxes. The recorded count is 291 of 1,047.

The validation box files in `C:\Users\elyas\OneDrive\Desktop\Negin\Mobihoc_Extention\Mobihoc_Extention\Negin_validation\P2\cooperscene\validation_inference` were replayed with the official rotation, the 3 m ego drop, the ±72 m window, and the 144 stored centers. The replay returned 291 disagreements on 1047 common regions.

| Vehicle | Misses of a union hit | Ego exclusion | Annotation coverage |
|---|---:|---:|---:|
| 1 | 168 | 0 | 168 |
| 2 | 143 | 0 | 143 |
| 3 | 113 | 0 | 113 |

| Region cause | Regions |
|---|---:|
| annotation_coverage_only | 291 |

The official rotation was applied to every stored ego box on all 30 validation frames (1274 boxes). The largest absolute residual against the stored world box is 2.132e-14 m. 0 boxes exceed 1e-6 m, 0 exceed 1 mm, and 0 exceed 1 cm.

Putting the ego-dropped boxes back removes 0 of the 291 disagreements and leaves 291. That restoration would also create 0 disagreements on regions that currently agree. Ego exclusion is therefore 0 of the recorded disagreements. The other 291 are annotation coverage.

| Vehicles missing the union hit | Regions |
|---|---:|
| 1 | 76 |
| 1+2 | 74 |
| 3 | 54 |
| 2+3 | 41 |
| 2 | 28 |
| 1+3 | 18 |

The median nearest kept box between two vehicles is 5.52 m over 1210 boxes. The 291 region-frames occupy 15 repeated centers. The map is `figures/gt_disagreement_map.png`. One coverage frame, 481380 at `grid_042`, is `figures/gt_annotation_coverage_example.png`. No ego-exclusion frame is drawn, because restoring the dropped boxes removes none of the 291.

This does affect the interpretation of the collective-error results. The shared label is broader than any one vehicle's annotations. A joint miss means all three detectors voted empty on a circle that at least one vehicle's annotators marked. It does not, by itself, mean that all three annotation sets contained that object. The primary scores stay on the union, which is the frozen rule. The 291 disagreements are not detector errors and were not used to choose a threshold.

## 2. Temporal robustness of R3

The paired moving-block bootstrap was repeated for the change in R3. Block lengths are 1, 2, 5, and 10 frames. Each length uses 2,000 draws and seed 77232. Blocks do not wrap from frame 481439 back to 481410. The interval is the 2.5 and 97.5 percentiles of policy R3 minus local R3. Length 1 is the published frame bootstrap. Local R3 is 0 on every resample, because no region in the export has all three local labels wrong, so the difference equals the policy's own R3 on each draw.

| Policy minus local | 1 frame | 2 frames | 5 frames | 10 frames |
|---|---|---|---|---|
| majority | [+0.0217, +0.0392] | [+0.0192, +0.0408] | [+0.0158, +0.0367] | [+0.0158, +0.0333] |
| weighted | [+0.0217, +0.0392] | [+0.0192, +0.0408] | [+0.0158, +0.0367] | [+0.0158, +0.0333] |
| conservative_f0 | [+0.0192, +0.0342] | [+0.0175, +0.0358] | [+0.0158, +0.0333] | [+0.0150, +0.0317] |
| expert_override | [+0.0192, +0.0342] | [+0.0175, +0.0358] | [+0.0158, +0.0333] | [+0.0150, +0.0317] |
| always_a | [+0.0792, +0.0950] | [+0.0767, +0.0983] | [+0.0750, +0.0983] | [+0.0750, +0.0967] |

The increase in all-agent failures stays supported for every non-local policy at every block length. Each lower endpoint is above zero. The intervals get somewhat wider as the block grows, and the lower endpoints move down, so temporal dependence makes the rise less precise. It does not remove it. This is unfavorable for the policies: accounting for repeated frames still leaves a higher R3 than local.

## 3. Smoke-test frame exclusion

Frame 481410 is the technical smoke-test frame. It is inside the primary 30-frame result. This section holds it out and rescores the same frozen labels. It does not refit the score, the radius, or the grid.

| Policy | 30-frame mean error | 29-frame mean error | 30-frame R2 | 29-frame R2 | 30-frame R3 | 29-frame R3 | 30-frame joint misses | 29-frame joint misses | 30-frame corrections | 29-frame corrections | 30-frame introduced | 29-frame introduced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| local | 0.0928 | 0.0928 | 0.0300 | 0.0302 | 0.0000 | 0.0000 | 0 | 0 | 0 | 0 | 0 | 0 |
| majority | 0.0300 | 0.0302 | 0.0300 | 0.0302 | 0.0300 | 0.0302 | 35 | 34 | 262 | 253 | 36 | 35 |
| weighted | 0.0300 | 0.0302 | 0.0300 | 0.0302 | 0.0300 | 0.0302 | 35 | 34 | 262 | 253 | 36 | 35 |
| conservative_f0 | 0.0603 | 0.0603 | 0.0300 | 0.0302 | 0.0267 | 0.0267 | 32 | 31 | 149 | 144 | 32 | 31 |
| expert_override | 0.0603 | 0.0603 | 0.0300 | 0.0302 | 0.0267 | 0.0267 | 32 | 31 | 149 | 144 | 32 | 31 |
| always_a | 0.0867 | 0.0871 | 0.0867 | 0.0871 | 0.0867 | 0.0871 | 101 | 98 | 197 | 190 | 175 | 170 |

Joint false alarms are in `frame_exclusion.csv`. Holding out 481410 is a sensitivity result. The primary claims stay on all 30 frames.

## 4. Unanimously annotated test regions

This is a secondary sensitivity. The primary evaluation remains the union of the three kept annotation sets on every exported test region. A region is retained here only when every vehicle's kept annotations agree with that union. Empty union regions are retained, because a miss by one vehicle would be a disagreement. Reliability rates, the score, the radius, and the grid are the frozen values.

Replaying the frozen grid on the test box files matched all 1200 exported regions. The unanimous subset retains 903 regions (2709 labels) and drops 297. 30 of the retained regions are positive, out of 327 positive regions in the full union.

| Policy | Regions | Mean error | R2 | R3 | Joint false alarms | Joint misses | Corrections | Introduced errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| local | 903 | 0.0022 | 0.0011 | 0.0000 | 0 | 0 | 0 | 0 |
| majority | 903 | 0.0011 | 0.0011 | 0.0011 | 1 | 0 | 4 | 1 |
| weighted | 903 | 0.0011 | 0.0011 | 0.0011 | 1 | 0 | 4 | 1 |
| conservative_f0 | 903 | 0.0015 | 0.0011 | 0.0000 | 0 | 0 | 2 | 0 |
| expert_override | 903 | 0.0015 | 0.0011 | 0.0000 | 0 | 0 | 2 | 0 |
| always_a | 903 | 0.0033 | 0.0033 | 0.0033 | 3 | 0 | 2 | 5 |

These rows do not replace the 1,200-region union table.
