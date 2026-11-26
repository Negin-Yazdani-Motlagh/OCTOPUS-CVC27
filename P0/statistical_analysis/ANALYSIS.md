# Paired sequence-level uncertainty

Nine regenerated sequences, 1,993 frames, 3,986 balanced queries. Each sequence is one cluster. A resample draws nine sequences with replacement, with equal probability, and keeps that same draw for every policy. The reported difference is the size-weighted pooled rate of the first policy minus the size-weighted pooled rate of the second. The interval is the 2.5th and 97.5th percentiles of 20,000 such differences. The generator is NumPy `default_rng(20261118)`.

Policies use the same labels as the earlier comparison. Local keeps both detector labels. Late fusion gives both agents the recorded late-fusion label. The disagreement gate uses late fusion only when the two local labels differ, and otherwise keeps the agreed local label. OR uses 1 when either local label is 1. F0 is omitted because it changed no label.

A negative difference means the first policy has the lower rate.

## Pooled differences

Denominators on the original nine sequences: mean error uses 7,972 agent labels, R2 uses 3,986 queries, and joint false negatives and false positives each use 1,993 queries. The bootstrap rebuilds those denominators from the sequences drawn in that replicate.

| Contrast | Metric | Observed difference | 95% interval | Replicates below, at, above 0 | Sequences below, at, above 0 |
|---|---|---:|---:|---:|---:|
| Late Fusion vs Local | Mean error | -9.571 pp | [-15.272, -5.248] pp | 20,000 / 0 / 0 | 9 / 0 / 0 |
| Late Fusion vs Local | R2 | +2.233 pp | [+0.882, +3.613] pp | 0 / 0 / 20,000 | 0 / 1 / 8 |
| Late Fusion vs Local | Joint false negatives | +0.000 pp | [+0.000, +0.000] pp | 0 / 20,000 / 0 | 0 / 9 / 0 |
| Late Fusion vs Local | Joint false positives | +4.466 pp | [+1.765, +7.227] pp | 0 / 0 / 20,000 | 0 / 1 / 8 |
| Disagreement Gate vs Local | Mean error | -9.621 pp | [-15.394, -5.268] pp | 20,000 / 0 / 0 | 9 / 0 / 0 |
| Disagreement Gate vs Local | R2 | +2.183 pp | [+0.843, +3.577] pp | 0 / 0 / 20,000 | 0 / 1 / 8 |
| Disagreement Gate vs Local | Joint false negatives | +0.000 pp | [+0.000, +0.000] pp | 0 / 20,000 / 0 | 0 / 9 / 0 |
| Disagreement Gate vs Local | Joint false positives | +4.365 pp | [+1.686, +7.153] pp | 0 / 0 / 20,000 | 0 / 1 / 8 |
| Disagreement Gate vs OR | Mean error | -0.176 pp | [-0.343, -0.034] pp | 19,892 / 108 / 0 | 4 / 5 / 0 |
| Disagreement Gate vs OR | R2 | -0.176 pp | [-0.343, -0.034] pp | 19,892 / 108 / 0 | 4 / 5 / 0 |
| Disagreement Gate vs OR | Joint false negatives | +0.000 pp | [+0.000, +0.000] pp | 0 / 20,000 / 0 | 0 / 9 / 0 |
| Disagreement Gate vs OR | Joint false positives | -0.351 pp | [-0.686, -0.067] pp | 19,892 / 108 / 0 | 4 / 5 / 0 |

## What the intervals say

Late fusion versus local moves the two error summaries in opposite directions. Mean error changes by -9.571 percentage points, from 1,151/7,972 to 388/7,972. The interval is [-15.272, -5.248] pp, and all 20,000 replicates are negative. R2 changes by +2.233 percentage points, from 105/3,986 to 194/3,986. The interval is [+0.882, +3.613] pp, and all 20,000 replicates are positive. Across sequences, the R2 difference is negative in 0, zero in 1, and positive in 8. The zero sequence is 0008, where both rates are 3/750.

The R2 increase is joint false positives. Joint false negatives are the same count for local, late fusion, the gate, and OR: 91/1,993. Positive queries on which those policies disagree: 0. The late-fusion joint-FN interval is [+0.000, +0.000] pp, and all 20,000 replicates are exactly zero. Joint false positives change by +4.466 percentage points, from 14/1,993 to 103/1,993. The interval is [+1.765, +7.227] pp, and all 20,000 replicates are positive. The sequence signs are 0 negative, 1 zero, and 8 positive.

The disagreement gate versus local has the same pattern. Mean error changes by -9.621 percentage points, interval [-15.394, -5.268] pp, and all 20,000 replicates are negative. R2 changes by +2.183 percentage points, from 105/3,986 to 192/3,986, interval [+0.843, +3.577] pp, and all 20,000 replicates are positive. Joint false positives change by +4.365 percentage points, from 14/1,993 to 101/1,993, interval [+1.686, +7.153] pp, and all 20,000 replicates are positive. Joint false negatives do not move.

The gate versus OR differs only where the two rules assign different labels. Mean error changes by -0.176 percentage points, from 398/7,972 to 384/7,972. The interval is [-0.343, -0.034] pp, and 19,892 replicates are negative, 108 are zero, and 0 are positive. R2 changes by -0.176 percentage points, from 199/3,986 to 192/3,986, interval [-0.343, -0.034] pp. Joint false positives change by -0.351 percentage points, from 108/1,993 to 101/1,993, interval [-0.686, -0.067] pp. Sequence signs for this R2 difference are 4 negative, 5 zero, and 0 positive. The four negative sequences are 0003, 0005, 0006, and 0008, by 1, 1, 4, and 1 query. A replicate is exactly zero when the draw misses all four. Joint false negatives do not move. For a shared-label policy, mean error equals R2, so the gate-versus-OR mean-error and R2 differences match. Their differences from local do not match, because local mean error counts every wrong agent and local R2 counts only queries where both agents are wrong.

## Sequence rates

These are the observed sequence rates. The bootstrap resamples rows of this table, not individual queries.

| Sequence | Queries | Local mean / R2 / FN / FP | Late fusion | Gate | OR |
|---|---:|---:|---:|---:|---:|
| 0000 | 294 | 73/588 = 12.41% · 4/294 = 1.36% · 4/147 · 0/147 | 12/588 = 2.04% · 6/294 = 2.04% · 4/147 · 2/147 | 12/588 = 2.04% · 6/294 = 2.04% · 4/147 · 2/147 | 12/588 = 2.04% · 6/294 = 2.04% · 4/147 · 2/147 |
| 0001 | 228 | 113/456 = 24.78% · 8/228 = 3.51% · 8/114 · 0/114 | 18/456 = 3.95% · 9/228 = 3.95% · 8/114 · 1/114 | 18/456 = 3.95% · 9/228 = 3.95% · 8/114 · 1/114 | 18/456 = 3.95% · 9/228 = 3.95% · 8/114 · 1/114 |
| 0002 | 288 | 155/576 = 26.91% · 10/288 = 3.47% · 10/144 · 0/144 | 22/576 = 3.82% · 11/288 = 3.82% · 10/144 · 1/144 | 22/576 = 3.82% · 11/288 = 3.82% · 10/144 · 1/144 | 22/576 = 3.82% · 11/288 = 3.82% · 10/144 · 1/144 |
| 0003 | 396 | 168/792 = 21.21% · 23/396 = 5.81% · 23/198 · 0/198 | 56/792 = 7.07% · 28/396 = 7.07% · 23/198 · 5/198 | 56/792 = 7.07% · 28/396 = 7.07% · 23/198 · 5/198 | 58/792 = 7.32% · 29/396 = 7.32% · 23/198 · 6/198 |
| 0004 | 360 | 58/720 = 8.06% · 7/360 = 1.94% · 4/180 · 3/180 | 44/720 = 6.11% · 22/360 = 6.11% · 4/180 · 18/180 | 44/720 = 6.11% · 22/360 = 6.11% · 4/180 · 18/180 | 44/720 = 6.11% · 22/360 = 6.11% · 4/180 · 18/180 |
| 0005 | 620 | 224/1240 = 18.06% · 22/620 = 3.55% · 19/310 · 3/310 | 110/1240 = 8.87% · 55/620 = 8.87% · 19/310 · 36/310 | 110/1240 = 8.87% · 55/620 = 8.87% · 19/310 · 36/310 | 112/1240 = 9.03% · 56/620 = 9.03% · 19/310 · 37/310 |
| 0006 | 608 | 126/1216 = 10.36% · 24/608 = 3.95% · 17/304 · 7/304 | 88/1216 = 7.24% · 44/608 = 7.24% · 17/304 · 27/304 | 88/1216 = 7.24% · 44/608 = 7.24% · 17/304 · 27/304 | 96/1216 = 7.89% · 48/608 = 7.89% · 17/304 · 31/304 |
| 0007 | 442 | 200/884 = 22.62% · 4/442 = 0.90% · 4/221 · 0/221 | 32/884 = 3.62% · 16/442 = 3.62% · 4/221 · 12/221 | 28/884 = 3.17% · 14/442 = 3.17% · 4/221 · 10/221 | 28/884 = 3.17% · 14/442 = 3.17% · 4/221 · 10/221 |
| 0008 | 750 | 34/1500 = 2.27% · 3/750 = 0.40% · 2/375 · 1/375 | 6/1500 = 0.40% · 3/750 = 0.40% · 2/375 · 1/375 | 6/1500 = 0.40% · 3/750 = 0.40% · 2/375 · 1/375 | 8/1500 = 0.53% · 4/750 = 0.53% · 2/375 · 2/375 |

The four numbers in each policy cell are mean error, R2, joint false negatives, and joint false positives. False-negative and false-positive denominators equal half the queries because every frame contributes one positive and one negative query.

## Equal-sequence-weight check

The primary interval weights a drawn sequence by its number of queries. A second interval gives each of the nine drawn sequences the same weight, then averages their rates. It answers a different question: the mean of sequence-level rates rather than the rate in the pooled query set. It is not a substitute for the pooled result.

| Contrast | Metric | Unweighted mean | 95% interval |
|---|---|---:|---:|
| Late Fusion vs Local | Mean error | -11.508 pp | [-16.611, -6.440] pp |
| Late Fusion vs Local | R2 | +2.025 pp | [+0.906, +3.256] pp |
| Late Fusion vs Local | Joint false negatives | +0.000 pp | [+0.000, +0.000] pp |
| Late Fusion vs Local | Joint false positives | +4.049 pp | [+1.813, +6.511] pp |
| Disagreement Gate vs Local | Mean error | -11.558 pp | [-16.683, -6.440] pp |
| Disagreement Gate vs Local | R2 | +1.974 pp | [+0.874, +3.193] pp |
| Disagreement Gate vs Local | Joint false negatives | +0.000 pp | [+0.000, +0.000] pp |
| Disagreement Gate vs Local | Joint false positives | +3.949 pp | [+1.747, +6.385] pp |
| Disagreement Gate vs OR | Mean error | -0.134 pp | [-0.283, -0.028] pp |
| Disagreement Gate vs OR | R2 | -0.134 pp | [-0.283, -0.028] pp |
| Disagreement Gate vs OR | Joint false negatives | +0.000 pp | [+0.000, +0.000] pp |
| Disagreement Gate vs OR | Joint false positives | -0.268 pp | [-0.566, -0.056] pp |

The signs match the pooled analysis. Magnitudes move because short sequences such as 0001, where local mean error is 24.78%, count the same as 0008, which has 750 queries and a local mean error of 2.27%.

## Limitations

There are only nine clusters. These intervals describe how the pooled difference moves when these nine recorded sequences are redrawn. They are not a population guarantee for other roads, sensors, or detectors. The published nine-sequence interval in `docs/EMPIRICAL_V2V4REAL_RESULTS.md` uses the same cluster design, 40,000 draws, and the same seed, for one contrast only: shared late-fusion joint error minus separate joint error. That published point estimate is the R2 difference computed here, 89/3,986. This run's 95% interval for that contrast is [+0.882, +3.613] pp. The published interval is +0.872 to +3.599 percentage points. The two percentile endpoints need not match digit for digit, because this run uses 20,000 draws.

Nine clusters make the bootstrap distribution coarse. There are 24,310 distinct multisets of nine sequences. A percentile interval at this size can miss the nominal 95% coverage. The draws treat sequences as independent. These nine validation sequences share one dataset, one sensor setup, and one pair of detectors, so dependence between sequences is not removed by clustering.

Clustering does keep within-sequence dependence intact. Frames in a sequence are consecutive, and the two queries in a frame share that frame. An event-level binomial interval would treat 3,986 queries as independent and would be too narrow. The cluster interval is the appropriate one for this dependence, and it is also much less precise than the query count suggests.

Sequences are not the same length. They range from 114 frames (228 queries) to 375 frames (750 queries). Equal-probability draws followed by pooling give a repeated long sequence more influence on the rate. The equal-weight check above is the comparison that removes that influence. Neither check creates more than nine observed clusters.

The twelve intervals are pointwise. They are not adjusted for looking at three contrasts and four metrics together.

Joint false-negative differences are exactly zero because local, late fusion, the gate, and OR are wrong on the same 91 positive queries and right on the other 1,902. The policies disagree on 0 positive queries. That is a property of these recorded labels. It is not a precise estimate of a zero effect on another dataset.

The rates are for the balanced diagnostic task: one ground-truth-anchored positive query and one negative query per frame, radius 7.5 m, score at least 0.30. They are not V2V4Real leaderboard scores, and the policies are rules applied to recorded outputs rather than detectors run again.

Files: `paired_differences.csv` holds the intervals, `per_sequence_numerators.csv` holds the counts, `bootstrap_replicates.csv` holds the 20,000 pooled differences, and `method.json` records the seed and percentile rule.
