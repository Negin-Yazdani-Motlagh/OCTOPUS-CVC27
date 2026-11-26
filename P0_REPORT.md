# P0 report: nine-sequence V2V4Real evidence

This report covers the balanced diagnostic task regenerated from DMSTrack commit `d3b9949499c8e68ea33060873bd1cb95b6d4d323`. The original converter, `Octopus-main/scripts/prepare_dmstrack_v2v4real.py`, was not modified. A region label is 1 when any retained Car center lies inside a circle in the KITTI X–Z plane. That is presence in a circle. It is not an object match, 3D IoU, average precision, or a natural prevalence rate. A separate bird’s-eye-view match of the 29 harmful rows is reported below and does not replace these labels. Ground truth places the regions. It is not an input to the adoption rule.

The published setting is radius 7.5 m and score 0.30: 9 sequences, 1,993 frames, 3,986 queries, 7,972 agent labels, and 1,993 queries of each class.

## Reproduced results

`P0/v2v4real_all/` holds the trace, provenance, `sequence_counts.csv`, and `source_manifest.json` for the 45 pinned text files. Those counts match the published nine-scene totals.

| Quantity | Count | Rate |
|---|---:|---:|
| Ego wrong | 670 / 3,986 | 16.81% |
| Partner wrong | 481 / 3,986 | 12.07% |
| CoBEVT wrong | 325 / 3,986 | 8.15% |
| Late fusion wrong | 194 / 3,986 | 4.87% |
| Both local detectors wrong | 105 / 3,986 | 2.63% |
| Shared late-fusion result wrong | 194 / 3,986 | 4.87% |
| Local mean error | 1,151 / 7,972 | 14.44% |

Sequence 0007 matches `docs/RESEARCH_GUIDE.md`: 221 frames and 442 queries; local mean error 200/884 = 22.62%; late fusion 32/884 = 3.62%; joint misses 4/221 for local, late fusion, and OR; joint false alarms 0, 12, and 10. The disagreement gate equals OR on this sequence, at 28/884 = 3.17%. Detail is in `P0/class_analysis/` and `P0/policy_comparison/`.

The fixed grid at the same setting also matches the published check: 23,916 queries, 4,052 positive, ego 1,020/23,916 = 4.26%, partner 1,718/23,916 = 7.18%, separate joint errors 291/23,916 = 1.22%, and late fusion 1,078/23,916 = 4.51%. Ego is more accurate than late fusion. The partner is less accurate.

Conservative two-agent F0, using the untouched `fusion_f0` block in `Octopus-main/examples/f0/v2v4real_f0.json`, accepts 250 of 442 decisions on 0007 and keeps local labels on 192. It changes no binary label. That is the result in `docs/F0_ONLINE_INTEGRATION.md`. See `P0/f0_real/`.

## New findings on all nine sequences

Class comparison is in `P0/class_analysis/per_sequence.csv` and `pooled.csv`. Policy comparison is in `P0/policy_comparison/per_sequence_policy.csv`.

Late fusion lowers mean error in every sequence and raises R2 in eight. Sequence 0008 is tied at 3/750. The pooled joint-miss count is 91/1,993 for local and for late fusion, and those are the same 91 positive queries. The entire R2 increase is joint false positives, from 14/1,993 to 103/1,993. Late fusion corrects 854 agent labels and introduces 91.

The locals disagree on 941/3,986 queries and on 905/1,993 frames. The late-fusion label is positive on 934 of those 941 disagreements. The other 7 are negative queries. The guide's statement that the cooperative candidate is positive on every disagreement is true for 0007 and false for the pooled data.

CoBEVT, broadcast to both agents, has mean error 650/7,972 = 8.15%. It is better than late fusion only on sequence 0006, where its mean error is 60/1,216 = 4.93% and late fusion is 88/1,216 = 7.24%.

F0 with the paper's two-agent settings accepts 3,045 queries and falls back on 941. Acceptance happens only when the two agents already agree, so the shared label replaces nothing. Every disagreement returns `KEEP_LOCAL`, because one supporting group cannot meet `min_supporting_groups` of 2. F0 changes 0 of 7,972 labels. Its errors equal local on every sequence. Per-sequence accepts are in `P0/f0_real/per_sequence_policy.csv`.

## Policy comparison and uncertainty

Pooled balanced results at 7.5 m and score 0.30:

| Policy | Mean error | Joint FN | Joint FP | R2 | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|
| Local | 1,151/7,972 = 14.44% | 91/1,993 | 14/1,993 | 105/3,986 = 2.63% | 0 | 0 |
| Late fusion | 388/7,972 = 4.87% | 91/1,993 | 103/1,993 | 194/3,986 = 4.87% | 854 | 91 |
| Disagreement gate | 384/7,972 = 4.82% | 91/1,993 | 101/1,993 | 192/3,986 = 4.82% | 854 | 87 |
| OR | 398/7,972 = 4.99% | 91/1,993 | 108/1,993 | 199/3,986 = 4.99% | 847 | 94 |
| AND | 1,904/7,972 = 23.88% | 938/1,993 | 14/1,993 | 952/3,986 = 23.88% | 94 | 847 |
| CoBEVT | 650/7,972 = 8.15% | 276/1,993 | 49/1,993 | 325/3,986 = 8.15% | 832 | 331 |

The gate equals OR on sequences 0000, 0001, 0002, 0004, and 0007. They differ on 7 queries, listed in `P0/policy_comparison/gate_or_differences.csv`: `0003_0173`, `0005_0269`, `0006_0000`, `0006_0044`, `0006_0214`, `0006_0290`, and `0008_0057`, all negative. On each, one local label is 1, late fusion is 0, OR is wrong, and the gate is right.

Uncertainty is a paired sequence-cluster bootstrap: 20,000 draws of the nine sequences, seed `20261118`, size-weighted pooled rates, and percentile intervals. Script and replicates: `P0/statistical_analysis/`. The difference is the first policy minus the second.

| Contrast | Mean error | R2 | Joint FN | Joint FP |
|---|---:|---:|---:|---:|
| Late fusion − local | −9.571 pp [−15.272, −5.248] | +2.233 pp [+0.882, +3.613] | 0 [0, 0] | +4.466 pp [+1.765, +7.227] |
| Gate − local | −9.621 pp [−15.394, −5.268] | +2.183 pp [+0.843, +3.577] | 0 [0, 0] | +4.365 pp [+1.686, +7.153] |
| Gate − OR | −0.176 pp [−0.343, −0.034] | −0.176 pp [−0.343, −0.034] | 0 [0, 0] | −0.351 pp [−0.686, −0.067] |

All 20,000 replicates keep the late-fusion and gate mean-error signs negative and their R2 signs positive. No sequence has a late-fusion R2 below its local R2. The R2 point estimate, 89/3,986, matches the published difference. The published interval used 40,000 draws and was +0.872 to +3.599 percentage points. Gate minus OR is negative in 19,892 replicates and exactly zero in 108, when the draw misses all four sequences that contain the seven differing queries. These intervals describe redraws of these nine sequences. They are not a population guarantee.

## Spatial sensitivity and the fixed grid

`P0/spatial_sensitivity/run_spatial_sensitivity.py` calls the original converter at radii 2.5, 5.0, and 7.5 m and scores 0.2, 0.3, and 0.5. Traces are under `traces/`. Tables are `balanced_policy.csv`, `fixed_grid_policy.csv`, `selection_by_radius.csv`, and `findings.csv`.

Every balanced setting still emits all 1,993 frames and 3,986 queries. Score does not move a query center. Positive anchors do not move with radius. Negative centers move on 525 frames at 2.5 m and 280 frames at 5.0 m, because a smaller circle accepts a nearer offset. Positive regions containing two or more ground-truth cars rise from 16 to 654 to 1,020. The label remains presence, not a car count. `topdown_examples.png` shows a rescued miss, a shared false alarm, and a shared miss from sequence 0007 at the published setting.

Across all nine balanced settings, late fusion has a lower pooled mean error and a higher pooled R2 than local. Identical joint-FN events, and a gate that is right on every disagreement with OR, hold only at 7.5 m and score 0.30. Elsewhere, late fusion is negative on some positive queries where the locals disagree. The gate copies that miss. OR keeps the local positive label, so its joint-FN count stays equal to local. At 2.5 m and score 0.50, OR mean error is 1,294/7,972 = 16.23% and the gate is 1,304/7,972 = 16.36%. At 5.0 m and score 0.50, the figures are 1,076/7,972 = 13.50% and 1,082/7,972 = 13.57%.

The fixed grid has 23,916 queries at every setting. Positive queries depend only on radius: 240, 1,786, and 4,052. At score 0.20 and radius 5.0 m or 7.5 m, late fusion's mean error is higher than the pooled local mean. Sharing still raises joint error relative to separate local labels.

## Harmful queries and three examples

`P0/spatial_audit/run_spatial_audit.py` recomputes all 35,874 trace labels with the converter. Mismatches: 0. A harmful case is a positive query where late fusion is wrong and at least one local detector is right. A repaired joint miss is a positive query where both locals are wrong and late fusion is right.

There are 29 harmful query-setting rows, covering 16 frames, and 0 repaired joint misses. The full list is `harmful_joint_misses.csv`. The published setting contributes 0 rows. Nineteen rows are passing late-fusion centers outside the circle. Ten are centers inside the circle whose scores fall below the cutoff. None have both locals correct.

| Example | Figure | What fails |
|---|---|---|
| `v2v4real_0003_0168_positive`, 2.5 m, score 0.30 | `spatial_audit/boundary.png` | Late-fusion and partner box 1, score 0.800, has its center 2.505 m from ground-truth track 45. The center is 5 mm outside the circle, so the label is 0, while the footprint crosses the circle. Ego box 1, score 0.736, is 0.303 m inside. |
| `v2v4real_0006_0179_positive`, 5.0 m, score 0.30 | `spatial_audit/score_cutoff.png` | Late-fusion box 8 and partner box 7 are 0.281 m from track 122, but their score is 0.291, below 0.30. Ego box 5, score 0.309, is 4.580 m inside. The nearest passing late-fusion box is 5.795 m outside. |
| `v2v4real_0005_0258_positive`, 7.5 m, score 0.20 | `spatial_audit/far_detection.png` | Partner box 15, score 0.208, is 0.851 m from track 213. The nearest passing late-fusion box, box 18, score 0.546, is 18.967 m away. The same frame is harmful at 2.5 m and 5.0 m. |

## Object-level match of those 29 rows

Region presence and object matching are different tests. Presence is 1 when any Car center that passes the score cutoff lies inside the circle. Object matching asks whether the anchor car, the ground-truth car that placed the positive query, receives a detection. The anchor center equals the query center on all 29 rows. A circle can contain other cars, so a local presence label can come from a car other than the anchor.

The check is in `P0/object_validation/`. Box fields and yaw were read from the same DMSTrack commit: `Object_3D.convert_to_trk_input_str` for the detection columns, and `Box3D.box2corners3d_camcoord` with `kitti_oxts.roty` for the rectangle. Before yaw, length lies along camera X and width along camera Z. The bird’s-eye-view polygon is that bottom face in X and Z. Height and camera Y are unused. Overlap is intersection area divided by union area. Thresholds 0.50 and 0.70 are separate passes. Each source keeps the score cutoff of that row. Within one frame, detections are taken from highest score to lowest, and each takes at most one still-unmatched ground-truth car. That is the one-to-one rule in OpenCOOD `caluclate_tp_fp`. Ego, the partner, and late fusion are matched separately. A row remains harmful only when late fusion is unmatched to the anchor and at least one local detector is matched.

`P0/object_validation/test_bev_iou.py` ran 11 geometric tests, all passing. The cases are identical rectangles, a half-turn of the same rectangle, separated rectangles, an axis-aligned shift with overlap 1/3, a smaller rectangle inside a larger one, a quarter-turn with overlap 1/3, and the score-order and larger-overlap assignment rules.

| IoU | Query-settings still harmful | Distinct frames still harmful |
|---|---:|---:|
| 0.50 | 21 / 29 | 10 / 16 |
| 0.70 | 20 / 29 | 9 / 16 |

Late fusion is unmatched to the anchor on every row. Its largest eligible overlap is 0.394. Every local match that remains harmful at 0.50 has overlap at least 0.632. On `0003_0168`, the late-fusion footprint crosses the 2.5 m circle, but its overlap with track 45 is 0.269 and ego’s is 0.790. One-to-one assignment did not move any of these anchors onto a different car.

Eight query-settings, six frames, leave the harmful set at 0.50 because the local center inside the circle is not an object match to the anchor. `0005_0258` at all three radii has partner overlap 0.400 with track 213. `0006_0009` has partner overlap 0.437 with track 13. `0006_0179` has an ego center 4.580 m away that does not overlap track 122; the box on the anchor scores 0.291, below 0.30, with overlap 0.650. `0006_0013` matches its in-circle ego box to track 3, not anchor 4. `0008_0133` matches its in-circle partner box to track 110, not anchor 7. `0003_0056` matches its in-circle ego box to track 18, not anchor 22.

`0006_0125` stays harmful at 0.50, with partner overlap 0.632, and drops out at 0.70. The nine frames that remain at 0.70 are `0003_0168`, `0003_0176`, `0003_0188`, `0004_0085`, `0004_0115`, `0005_0018`, `0006_0215`, `0007_0069`, and `0007_0141`. Side-by-side labels are in `harmful_object_matches.csv`. The write-up is `ANALYSIS.md`.

This check does not replace the region benchmark, and it was not run on the other queries. It is not 3D IoU, image IoU, or average precision. The ground-truth image boxes in this export are zero, and camera Y is unused, so the vertical origin is untested. Boxes below the original score cutoff stay ineligible. The geometric tests use constructed rectangles. They do not replay DMSTrack’s convex-hull routine on these frames.

## Paired outcomes, source baselines, and temporal blocks

`P0/acceptance_audit/` adds the three tables that the first P0 pass left open. A paired outcome is the local pair versus one broadcast label on the same query: both correct as a joint event, a rescued joint failure, an introduced joint failure, or a failure that remains. Sequence 0007 under late fusion is 426, 0, 12, and 4 out of 442 queries, which is the count in `tests/test_cvc_figure_study.py`.

Late fusion rescues 0 joint failures in all nine sequences. It introduces 89, all on negative queries, and it leaves the original 105 joint failures in place. Every frame has both a positive and a negative query. Late fusion is correct on both queries in 1,808 of 1,993 frames. The per-sequence counts are in `paired_outcome_transitions.csv`.

Always-ego copies the ego label onto both agents. Always-partner copies the partner label. Neither can rescue a joint failure, because the copied detector is already one of the two locals.

| Rule | Mean error | R2 | Rescued | Introduced | Frames correct on both queries |
|---|---:|---:|---:|---:|---:|
| Local, separate labels | 1,151/7,972 = 14.44% | 105/3,986 = 2.63% | — | — | — |
| Always-ego | 1,340/7,972 = 16.81% | 670/3,986 = 16.81% | 0 | 565 | 1,338/1,993 |
| Always-partner | 962/7,972 = 12.07% | 481/3,986 = 12.07% | 0 | 376 | 1,526/1,993 |
| Late fusion | 388/7,972 = 4.87% | 194/3,986 = 4.87% | 0 | 89 | 1,808/1,993 |

Always-ego is worse than the two-local average on mean error. Always-partner is better than that average and still well above late fusion. Both raise R2. CoBEVT is the only broadcast in this set that rescues any joint failure: 35 queries, 29 of them positive. On sequence 0006 it remains the lower mean-error rule, 60/1,216 = 4.93% against late fusion at 88/1,216 = 7.24%.

The new bootstrap uses 20,000 replicates and seed `20261118`. Redrawing the nine sequences reproduces the earlier late-fusion-minus-local intervals, mean error [−15.272, −5.248] percentage points and R2 [+0.882, +3.613]. A second design keeps every sequence and resamples frames inside it with a circular moving block of 1, 6, 12, or 24 frames. The two queries in a frame stay together. At every block length the pooled intervals still exclude 0. The 24-frame intervals are mean error [−10.273, −8.881] and R2 [+1.781, +2.709]. They are narrower because they do not redraw which scenes are present.

Within a single sequence, a 12-frame block leaves the R2 increase compatible with 0 for 0000, 0001, 0002, and 0008. Sequence 0004’s mean-error interval touches 0 at 12 frames and is [−3.750, +0.139] at 24 frames. The pooled within-sequence interval and the nine-scene interval answer different questions.

## Claims that stand, and claims that do not

These published claims stand at 7.5 m and score 0.30, with the denominators above.

- The nine-scene marginal and joint counts, including the +2.233 percentage-point joint-error increase.
- The 0007 class split, including gate equals OR on that sequence only.
- Late fusion lowers pooled mean error and raises pooled R2. The sequence bootstrap intervals exclude zero. Sequence 0008 does not show an R2 increase.
- Two-agent F0 changes no label, on 0007 and on the other eight sequences.
- On the fixed grid, late fusion is not more accurate than the ego detector.

These stronger readings do not survive the rest of the evidence.

- Gate equals OR is not a property of the nine sequences. It holds for 5 sequences at the published setting, and that count changes with radius and score.
- The gate is not always right where it differs from OR, and it is not always the lower-error rule. At the published setting the 7 differences are negative and the gate is right. In the other eight radius-score settings, some differences are positive queries, and the gate adopts a late-fusion miss. OR then has the lower mean error at 2.5 m / 0.50 and 5.0 m / 0.50.
- Joint false negatives are not invariant to sharing except at the published setting. The other settings contain the 29 harmful region rows above. Late fusion repairs no joint miss in the sweep. Those 29 rows are circle-presence failures. Object matching of the same rows leaves 10 of the 16 frames harmful at IoU 0.50 and 9 of 16 at IoU 0.70. Late fusion still receives none of the 16 anchor cars.
- The late-fusion label is not positive on every disagreement. It is negative on the 7 listed queries.
- A lower balanced-task mean error does not mean both vehicles improve on every task. The fixed grid is the counterexample already published for 7.5 m / 0.30, and it also reverses the pooled mean-error comparison at score 0.20 for radii 5.0 m and 7.5 m.
- Privileging one local source does not explain the late-fusion gain. Always-ego raises mean error. Always-partner lowers it only to 12.07%, and both rules raise R2 because they cannot repair a joint miss.

## Acceptance audit

Section 6 asks for regenerated traces, an archived-count check, class-specific joint errors, mean errors, complete frames, paired transitions, the 0007 rules without forcing equality, CoBEVT, an always-A source rule, F0, calibration only on held-out scenes, a per-sequence CSV, a source manifest, and uncertainty from sequence or temporal blocks. The spatial paragraph asks for the coordinate audit, the published radius and score, the fixed grid, a small radius-score sweep, and top-down plots that say what a binary query measures.

| Criterion | Status | Where it stands |
|---|---|---|
| Nine traces from the pinned DMSTrack commit | Complete | `P0/v2v4real_all/`, commit `d3b9949499c8e68ea33060873bd1cb95b6d4d323`, 45 text files in `source_manifest.json` |
| Compare aggregates to the archived CSV | Blocked on one external file | Regenerated counts match the published totals. `empirical/v2v4real/sequence_counts.csv` is not in the tree, so `--check` was not run |
| Class-specific joint FN/FP, mean errors, complete frames, paired transitions | Complete | `P0/class_analysis/`, `P0/policy_comparison/`, and `P0/acceptance_audit/paired_outcome_transitions.csv` |
| 0007 OR, AND, and gate, without forcing equality | Complete | Gate equals OR on 0007 and on four other sequences. Seven queries differ elsewhere |
| CoBEVT kept separate | Complete | Separate rows in the policy table. It is better than late fusion only on 0006 |
| Always-A when privileging a source | Complete | Always-ego and always-partner in `always_source_baselines.csv` |
| F0 at the paper settings | Complete as an offline rule | 0 of 7,972 labels change. Deadline and energy were not replayed on all nine sequences |
| No threshold fit on the reported scenes | Complete | The radius-score grid was prespecified. Nothing was tuned |
| Per-sequence CSV, denominators, source manifest | Complete | Sequence counts, policy rows, and the manifest |
| Sequence or temporal-block uncertainty | Complete for both designs | Sequence clusters in `P0/statistical_analysis/`. Blocks of 1, 6, 12, and 24 frames in `temporal_block_bootstrap.csv` |
| Coordinate audit, 7.5 m, score 0.30, fixed grid, radius-score sweep | Complete | `P0/spatial_audit/` and `P0/spatial_sensitivity/` |
| Top-down plots and the meaning of a binary query | Complete | Presence in a circle. Multiple cars still produce one label. The plots are not 3D IoU or average precision |

## Limitations

`empirical/v2v4real/sequence_counts.csv`, `empirical/v2v4real/packed_outcomes.json`, `examples/v2v4real_real_seq0007/trace.jsonl`, and the two CooperScene files under `samples/three_vehicle_real_published/` are absent. Those five paths are the 23 upstream test failures. The exact request is `P0/acceptance_audit/LEWIS_FILE_REQUEST.md`.

F0 on these nine sequences is an offline label rule. This pass does not assign it deadline or energy on every sequence. The balanced task forces one positive and one negative query per frame. Nine clusters make the scene-level percentile intervals coarse: there are 24,310 possible multisets, the sequences share one dataset, and the intervals are pointwise. The within-sequence blocks condition on these nine recordings. Object matching covers the 29 harmful region rows and the anchor car only. It does not use 3D overlap. A local presence label can be right about the circle while missing the anchor, which is why 6 of the 16 frames leave the harmful set at IoU 0.50.
