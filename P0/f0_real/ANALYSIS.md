# Conservative two-agent F0 on nine real sequences

Settings are the untouched `examples/f0/v2v4real_f0.json` fusion block: assumed error 0.06 for ego and 0.10 for the partner, confidence at least 0.90, at least two independent groups, at least two groups supporting the winner, conflict fraction at most 0.40, source error below 0.25, and age below 120 ms. Each agent is its own dependence group. The prior is 0.5. No threshold was changed.

F0 sees only the two local binary labels. It does not see ground truth, late fusion, or CoBEVT. The other two policies are the same label rules as the previous comparison: the disagreement gate adopts late fusion only when the locals differ, and OR adopts 1 if either local label is 1.

## Sequence 0007 matches the paper

`docs/F0_ONLINE_INTEGRATION.md` reports that F0 accepted 250 of 442 decisions, kept local labels on 192, and corrected none. Mean error stayed at the local 22.624%, and both-agent error stayed at 4/442.
- Accepted 250/442, fallback 192/442.
- Mean error 200/884 = 22.62%, identical to local.
- R2 4/442, joint FN 4/221, joint FP 0/221.
- Corrected labels 0, introduced labels 0.

## F0 changes no binary label

Across all 3,986 queries and 7,972 agent labels, the F0 label differs from the local label zero times. On every sequence, F0's mean error, R2, joint FN, and joint FP equal Local, and corrected and introduced counts are zero.

There are only two vote patterns, and both are forced by the two-support rule.

- The agents agree on 3,045 queries. Both dependence groups support that label. The surrogate confidence is 0.993, above 0.90, and conflict is zero, so F0 accepts and shares the label. Both agents already held it, so the shared result replaces nothing.
- The agents disagree on 941 queries. One group supports 0 and one supports 1. The winner has only one supporting group, below the required two. The conflict fraction is 0.50, above 0.40. Confidence is 0.635, below 0.90. F0 returns `KEEP_LOCAL` for all three reasons: `insufficient_independent_support_for_winner`, `excessive_conflict`, and `low_surrogate_confidence`. Each agent keeps its own label.

A two-agent disagreement can never produce two groups on the same side. With `min_supporting_groups` set to 2, F0 cannot adopt either side, and it cannot adopt a third detector. Acceptance is possible only when the agents already agree.

## Aggregate, 3,986 queries

Denominators: 1,993 positive queries, 1,993 negative queries, 7,972 agent labels. F0's accepted and fallback counts use the 3,986 queries.

| Policy | Mean error | R2 | Joint FN | Joint FP | Accepted | Fallback | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Local | 1151/7972 = 14.44% | 105/3986 = 2.63% | 91/1993 = 4.57% | 14/1993 = 0.70% | — | — | 0 | 0 |
| F0 | 1151/7972 = 14.44% | 105/3986 = 2.63% | 91/1993 = 4.57% | 14/1993 = 0.70% | 3045 | 941 | 0 | 0 |
| Disagreement Gate | 384/7972 = 4.82% | 192/3986 = 4.82% | 91/1993 = 4.57% | 101/1993 = 5.07% | — | — | 854 | 87 |
| OR | 398/7972 = 4.99% | 199/3986 = 4.99% | 91/1993 = 4.57% | 108/1993 = 5.42% | — | — | 847 | 94 |

The gate and OR correct hundreds of agent labels. F0 corrects none. Their lower mean error comes from sharing a label the two local detectors did not both already hold. F0's rule forbids that share.

## Per sequence

### 0000 — 294 queries, 147 positive, 147 negative

| Policy | Mean error | R2 | Joint FN | Joint FP | Accepted | Fallback | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Local | 73/588 = 12.41% | 4/294 = 1.36% | 4/147 | 0/147 | — | — | 0 | 0 |
| F0 | 73/588 = 12.41% | 4/294 = 1.36% | 4/147 | 0/147 | 229 | 65 | 0 | 0 |
| Disagreement Gate | 12/588 = 2.04% | 6/294 = 2.04% | 4/147 | 2/147 | — | — | 63 | 2 |
| OR | 12/588 = 2.04% | 6/294 = 2.04% | 4/147 | 2/147 | — | — | 63 | 2 |

### 0001 — 228 queries, 114 positive, 114 negative

| Policy | Mean error | R2 | Joint FN | Joint FP | Accepted | Fallback | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Local | 113/456 = 24.78% | 8/228 = 3.51% | 8/114 | 0/114 | — | — | 0 | 0 |
| F0 | 113/456 = 24.78% | 8/228 = 3.51% | 8/114 | 0/114 | 131 | 97 | 0 | 0 |
| Disagreement Gate | 18/456 = 3.95% | 9/228 = 3.95% | 8/114 | 1/114 | — | — | 96 | 1 |
| OR | 18/456 = 3.95% | 9/228 = 3.95% | 8/114 | 1/114 | — | — | 96 | 1 |

### 0002 — 288 queries, 144 positive, 144 negative

| Policy | Mean error | R2 | Joint FN | Joint FP | Accepted | Fallback | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Local | 155/576 = 26.91% | 10/288 = 3.47% | 10/144 | 0/144 | — | — | 0 | 0 |
| F0 | 155/576 = 26.91% | 10/288 = 3.47% | 10/144 | 0/144 | 153 | 135 | 0 | 0 |
| Disagreement Gate | 22/576 = 3.82% | 11/288 = 3.82% | 10/144 | 1/144 | — | — | 134 | 1 |
| OR | 22/576 = 3.82% | 11/288 = 3.82% | 10/144 | 1/144 | — | — | 134 | 1 |

### 0003 — 396 queries, 198 positive, 198 negative

| Policy | Mean error | R2 | Joint FN | Joint FP | Accepted | Fallback | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Local | 168/792 = 21.21% | 23/396 = 5.81% | 23/198 | 0/198 | — | — | 0 | 0 |
| F0 | 168/792 = 21.21% | 23/396 = 5.81% | 23/198 | 0/198 | 274 | 122 | 0 | 0 |
| Disagreement Gate | 56/792 = 7.07% | 28/396 = 7.07% | 23/198 | 5/198 | — | — | 117 | 5 |
| OR | 58/792 = 7.32% | 29/396 = 7.32% | 23/198 | 6/198 | — | — | 116 | 6 |

### 0004 — 360 queries, 180 positive, 180 negative

| Policy | Mean error | R2 | Joint FN | Joint FP | Accepted | Fallback | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Local | 58/720 = 8.06% | 7/360 = 1.94% | 4/180 | 3/180 | — | — | 0 | 0 |
| F0 | 58/720 = 8.06% | 7/360 = 1.94% | 4/180 | 3/180 | 316 | 44 | 0 | 0 |
| Disagreement Gate | 44/720 = 6.11% | 22/360 = 6.11% | 4/180 | 18/180 | — | — | 29 | 15 |
| OR | 44/720 = 6.11% | 22/360 = 6.11% | 4/180 | 18/180 | — | — | 29 | 15 |

### 0005 — 620 queries, 310 positive, 310 negative

| Policy | Mean error | R2 | Joint FN | Joint FP | Accepted | Fallback | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Local | 224/1240 = 18.06% | 22/620 = 3.55% | 19/310 | 3/310 | — | — | 0 | 0 |
| F0 | 224/1240 = 18.06% | 22/620 = 3.55% | 19/310 | 3/310 | 440 | 180 | 0 | 0 |
| Disagreement Gate | 110/1240 = 8.87% | 55/620 = 8.87% | 19/310 | 36/310 | — | — | 147 | 33 |
| OR | 112/1240 = 9.03% | 56/620 = 9.03% | 19/310 | 37/310 | — | — | 146 | 34 |

### 0006 — 608 queries, 304 positive, 304 negative

| Policy | Mean error | R2 | Joint FN | Joint FP | Accepted | Fallback | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Local | 126/1216 = 10.36% | 24/608 = 3.95% | 17/304 | 7/304 | — | — | 0 | 0 |
| F0 | 126/1216 = 10.36% | 24/608 = 3.95% | 17/304 | 7/304 | 530 | 78 | 0 | 0 |
| Disagreement Gate | 88/1216 = 7.24% | 44/608 = 7.24% | 17/304 | 27/304 | — | — | 58 | 20 |
| OR | 96/1216 = 7.89% | 48/608 = 7.89% | 17/304 | 31/304 | — | — | 54 | 24 |

### 0007 — 442 queries, 221 positive, 221 negative

| Policy | Mean error | R2 | Joint FN | Joint FP | Accepted | Fallback | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Local | 200/884 = 22.62% | 4/442 = 0.90% | 4/221 | 0/221 | — | — | 0 | 0 |
| F0 | 200/884 = 22.62% | 4/442 = 0.90% | 4/221 | 0/221 | 250 | 192 | 0 | 0 |
| Disagreement Gate | 28/884 = 3.17% | 14/442 = 3.17% | 4/221 | 10/221 | — | — | 182 | 10 |
| OR | 28/884 = 3.17% | 14/442 = 3.17% | 4/221 | 10/221 | — | — | 182 | 10 |

### 0008 — 750 queries, 375 positive, 375 negative

| Policy | Mean error | R2 | Joint FN | Joint FP | Accepted | Fallback | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Local | 34/1500 = 2.27% | 3/750 = 0.40% | 2/375 | 1/375 | — | — | 0 | 0 |
| F0 | 34/1500 = 2.27% | 3/750 = 0.40% | 2/375 | 1/375 | 722 | 28 | 0 | 0 |
| Disagreement Gate | 6/1500 = 0.40% | 3/750 = 0.40% | 2/375 | 1/375 | — | — | 28 | 0 |
| OR | 8/1500 = 0.53% | 4/750 = 0.53% | 2/375 | 2/375 | — | — | 27 | 1 |

Machine-readable rows are in `per_sequence_policy.csv`.
