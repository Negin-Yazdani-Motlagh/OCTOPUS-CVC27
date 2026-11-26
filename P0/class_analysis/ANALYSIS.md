# Class-specific Local vs Late Fusion, nine sequences

Source trace: `Negin_validation/P0/v2v4real_all/trace.jsonl` (3,986 queries, 1,993 frames). No original source file was edited.

Each query has one ground-truth bit and two local predictions, ego and partner. Late fusion is the recorded cooperative label. Both agents adopt that one label, so a late-fusion mistake is a joint mistake. Counts below use these definitions.

- Mean individual error: wrong agent labels divided by agent labels. Local has two labels per query. Late fusion assigns the same label to both, so its mean equals its query error rate.
- Joint false negative: truth is positive and both agents are wrong. Denominator is the positive queries.
- Joint false positive: truth is negative and both agents are wrong. Denominator is the negative queries.
- Local disagreement: the two local predictions differ.
- Corrected agent label: that agent was wrong locally and the late-fusion label is right.
- Introduced agent label: that agent was right locally and the late-fusion label is wrong.

## Sequence 0007 matches the paper

`docs/RESEARCH_GUIDE.md` gives the 0007 class result: 221 positive and 221 negative queries; local detectors disagree 192 times (182 positive, 10 negative); 183 of 221 frames disagree; the cooperative candidate is positive on every disagreement; joint misses are 4 for local and for shared late fusion; joint false alarms are 0 for local and 12 for late fusion; mean error is 22.62% local and 3.62% late fusion. The same paragraph says the disagreement gate equals OR, with joint false alarms 10 and mean error 3.17% for that OR rule.

The regenerated 0007 trace matches every one of those figures.

| Check | Paper | Regenerated trace |
|---|---|---|
| Queries | 221 positive, 221 negative | 221 / 221 |
| Disagreements | 192 (182 positive, 10 negative) | 192 (182, 10) |
| Frames with a disagreement | 183 / 221 | 183 / 221 |
| Cooperative label on disagreements | positive on all 192 | positive on all 192 |
| Joint misses | 4 local, 4 late fusion, 4 OR | 4, 4, 4 |
| Joint false alarms | 0 local, 12 late fusion, 10 OR | 0, 12, 10 |
| Mean individual error | 22.62% local, 3.62% late fusion, 3.17% OR | 200/884 = 22.62%, 16/442 = 3.62%, 28/884 = 3.17% |
| Disagreement gate equals OR | yes, on this trace only | yes |

Agent-level changes on 0007, which the paragraph does not list separately: late fusion corrects 182 of 884 agent labels and introduces 14. Net agent errors go from 200 to 32.

## All nine sequences

Positive and negative queries are equal in every sequence, one of each per frame.

Local mean error uses two labels per query, so its denominator is twice the query count. Late fusion gives both agents one shared label, so its denominator is the query count. Joint false negatives use the positive queries. Joint false positives use the negative queries.

| Sequence | Queries | Local mean error | Late-fusion mean error | Joint FN local | Joint FN late | Joint FP local | Joint FP late | Disagreements | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0000 | 294 | 73/588 = 12.41% | 6/294 = 2.04% | 4/147 = 2.72% | 4/147 = 2.72% | 0/147 = 0 | 2/147 = 1.36% | 65/294 = 22.11% | 63/588 | 2/588 |
| 0001 | 228 | 113/456 = 24.78% | 9/228 = 3.95% | 8/114 = 7.02% | 8/114 = 7.02% | 0/114 = 0 | 1/114 = 0.88% | 97/228 = 42.54% | 96/456 | 1/456 |
| 0002 | 288 | 155/576 = 26.91% | 11/288 = 3.82% | 10/144 = 6.94% | 10/144 = 6.94% | 0/144 = 0 | 1/144 = 0.69% | 135/288 = 46.88% | 134/576 | 1/576 |
| 0003 | 396 | 168/792 = 21.21% | 28/396 = 7.07% | 23/198 = 11.62% | 23/198 = 11.62% | 0/198 = 0 | 5/198 = 2.53% | 122/396 = 30.81% | 117/792 | 5/792 |
| 0004 | 360 | 58/720 = 8.06% | 22/360 = 6.11% | 4/180 = 2.22% | 4/180 = 2.22% | 3/180 = 1.67% | 18/180 = 10.00% | 44/360 = 12.22% | 29/720 | 15/720 |
| 0005 | 620 | 224/1,240 = 18.06% | 55/620 = 8.87% | 19/310 = 6.13% | 19/310 = 6.13% | 3/310 = 0.97% | 36/310 = 11.61% | 180/620 = 29.03% | 147/1,240 | 33/1,240 |
| 0006 | 608 | 126/1,216 = 10.36% | 44/608 = 7.24% | 17/304 = 5.59% | 17/304 = 5.59% | 7/304 = 2.30% | 27/304 = 8.88% | 78/608 = 12.83% | 58/1,216 | 20/1,216 |
| 0007 | 442 | 200/884 = 22.62% | 16/442 = 3.62% | 4/221 = 1.81% | 4/221 = 1.81% | 0/221 = 0 | 12/221 = 5.43% | 192/442 = 43.44% | 182/884 | 14/884 |
| 0008 | 750 | 34/1,500 = 2.27% | 3/750 = 0.40% | 2/375 = 0.53% | 2/375 = 0.53% | 1/375 = 0.27% | 1/375 = 0.27% | 28/750 = 3.73% | 28/1,500 | 0/1,500 |
| All | 3,986 | 1,151/7,972 = 14.44% | 194/3,986 = 4.87% | 91/1,993 = 4.57% | 91/1,993 = 4.57% | 14/1,993 = 0.70% | 103/1,993 = 5.17% | 941/3,986 = 23.61% | 854/7,972 | 91/7,972 |

The all-sequence rates, 14.44% and 4.87%, match the nine-scene totals in the research guide. Both-separate joint error is 105/3,986 = 2.63%, and shared late-fusion error is 194/3,986 = 4.87%, also matching that guide.

## What does not carry over from 0007

Joint misses are the same 91 events for local and late fusion, in every sequence. Late fusion does not repair a double miss, and it does not create one. The accuracy gain is entirely from fixing a single local mistake. Across all sequences that is 854 corrected agent labels against 91 introduced ones.

The new errors are joint false alarms. Local joint false positives are 14/1,993. Late fusion raises that to 103/1,993. Sequences 0000, 0001, 0002, 0003, and 0007 have no local joint false alarm. Only 0008 keeps the joint false-alarm count unchanged, at 1, and it introduces no agent error.

The 0007 statement that the cooperative label is positive on every disagreement, and that the disagreement gate equals OR, is true for 0000, 0001, 0002, 0004, and 0007. It is not true for the other four:

| Sequence | Cooperative label positive on disagreements | Gate equals OR |
|---|---|---|
| 0003 | 121 / 122 | no |
| 0005 | 179 / 180 | no |
| 0006 | 74 / 78 | no |
| 0008 | 27 / 28 | no |

Machine-readable counts are in `per_sequence.csv` and `pooled.csv`.
