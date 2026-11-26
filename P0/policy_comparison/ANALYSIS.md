# Six-policy comparison on nine V2V4Real sequences

Traces: `Negin_validation/P0/v2v4real_all/trace.jsonl` and `provenance.jsonl`. No original source file was edited.

Two agents, ego and partner. A broadcast policy gives both agents the same label, so a wrong broadcast makes both wrong and mean error equals R2. Local keeps each agent's own label.

- **Local:** each agent keeps its detector label.
- **Always Late Fusion:** both adopt the recorded late-fusion label.
- **Disagreement Gate:** if the local labels differ, both adopt late fusion; if they agree, both keep that shared local label.
- **OR:** both adopt 1 if either local label is 1.
- **AND:** both adopt 1 only if both local labels are 1.
- **Always CoBEVT:** both adopt the recorded CoBEVT label from provenance.

Mean error, corrected labels, and introduced labels use agent labels (2 per query). Joint false negatives use positive queries. Joint false positives use negative queries. R2 is queries where both agents are wrong, over all queries. With two agents, R2 count equals joint false negatives plus joint false positives. Corrected means a local error that the policy label fixes. Introduced means a locally correct label that the policy label breaks. Local therefore has zero corrected and zero introduced labels.

## Sequence 0007 matches the paper

The class paragraph in `docs/RESEARCH_GUIDE.md` says joint misses are 4 for local, late fusion, and OR; joint false alarms are 0, 12, and 10; mean error is 22.62% local, 3.62% late fusion, and 3.17% for the disagreement gate and OR, which are equal on this trace.

- Local mean error 200/884 = 22.62%; joint FN 4/221; joint FP 0/221; R2 4/442.
- Late fusion mean error 32/884 = 3.62%; joint FN 4/221; joint FP 12/221; R2 16/442.
- Gate and OR are identical: mean error 28/884 = 3.17%; joint FN 4/221; joint FP 10/221; R2 14/442.
- No event in 0007 has a different gate label and OR label.

## Aggregate, 3,986 queries

Denominators: 1,993 positive queries, 1,993 negative queries, 7,972 agent labels.

| Policy | Mean error | Joint FN | Joint FP | R2 | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|
| Local | 1151/7972 = 14.44% | 91/1993 = 4.57% | 14/1993 = 0.70% | 105/3986 = 2.63% | 0/7972 | 0/7972 |
| Always Late Fusion | 388/7972 = 4.87% | 91/1993 = 4.57% | 103/1993 = 5.17% | 194/3986 = 4.87% | 854/7972 | 91/7972 |
| Disagreement Gate | 384/7972 = 4.82% | 91/1993 = 4.57% | 101/1993 = 5.07% | 192/3986 = 4.82% | 854/7972 | 87/7972 |
| OR | 398/7972 = 4.99% | 91/1993 = 4.57% | 108/1993 = 5.42% | 199/3986 = 4.99% | 847/7972 | 94/7972 |
| AND | 1904/7972 = 23.88% | 938/1993 = 47.06% | 14/1993 = 0.70% | 952/3986 = 23.88% | 94/7972 | 847/7972 |
| Always CoBEVT | 650/7972 = 8.15% | 276/1993 = 13.85% | 49/1993 = 2.46% | 325/3986 = 8.15% | 832/7972 | 331/7972 |

## Where the Disagreement Gate and OR differ

They differ on 7 of 3,986 queries. In every case the locals disagree, the truth is negative, OR outputs 1, and the gate adopts late fusion's 0. The gate is correct on all 7. OR is wrong on all 7. None of these events is in sequence 0007.

| Sequence | Event | Locals (ego, partner) | Late fusion | OR | Gate | Correct policy |
|---|---|---|---:|---:|---:|---|
| 0003 | `v2v4real_0003_0173_negative` | 1, 0 | 0 | 1 | 0 | disagreement_gate |
| 0005 | `v2v4real_0005_0269_negative` | 0, 1 | 0 | 1 | 0 | disagreement_gate |
| 0006 | `v2v4real_0006_0000_negative` | 1, 0 | 0 | 1 | 0 | disagreement_gate |
| 0006 | `v2v4real_0006_0044_negative` | 0, 1 | 0 | 1 | 0 | disagreement_gate |
| 0006 | `v2v4real_0006_0214_negative` | 0, 1 | 0 | 1 | 0 | disagreement_gate |
| 0006 | `v2v4real_0006_0290_negative` | 1, 0 | 0 | 1 | 0 | disagreement_gate |
| 0008 | `v2v4real_0008_0057_negative` | 1, 0 | 0 | 1 | 0 | disagreement_gate |

Those seven false alarms are why OR has 108 joint false positives and the gate has 101. Their joint-miss counts stay equal, at 91, because they never disagree on a positive query in this trace.

## Per sequence

Each sequence has one positive and one negative query per frame, so the positive and negative denominators are half the query count. Agent-label denominators are twice the query count. Corrected and introduced counts use that agent-label denominator.

### 0000 — 294 queries, 147 positive, 147 negative, 588 agent labels

| Policy | Mean error | Joint FN | Joint FP | R2 | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|
| Local | 73/588 = 12.41% | 4/147 = 2.72% | 0/147 = 0.00% | 4/294 = 1.36% | 0 | 0 |
| Always Late Fusion | 12/588 = 2.04% | 4/147 = 2.72% | 2/147 = 1.36% | 6/294 = 2.04% | 63 | 2 |
| Disagreement Gate | 12/588 = 2.04% | 4/147 = 2.72% | 2/147 = 1.36% | 6/294 = 2.04% | 63 | 2 |
| OR | 12/588 = 2.04% | 4/147 = 2.72% | 2/147 = 1.36% | 6/294 = 2.04% | 63 | 2 |
| AND | 134/588 = 22.79% | 67/147 = 45.58% | 0/147 = 0.00% | 67/294 = 22.79% | 2 | 63 |
| Always CoBEVT | 122/588 = 20.75% | 61/147 = 41.50% | 0/147 = 0.00% | 61/294 = 20.75% | 13 | 62 |

### 0001 — 228 queries, 114 positive, 114 negative, 456 agent labels

| Policy | Mean error | Joint FN | Joint FP | R2 | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|
| Local | 113/456 = 24.78% | 8/114 = 7.02% | 0/114 = 0.00% | 8/228 = 3.51% | 0 | 0 |
| Always Late Fusion | 18/456 = 3.95% | 8/114 = 7.02% | 1/114 = 0.88% | 9/228 = 3.95% | 96 | 1 |
| Disagreement Gate | 18/456 = 3.95% | 8/114 = 7.02% | 1/114 = 0.88% | 9/228 = 3.95% | 96 | 1 |
| OR | 18/456 = 3.95% | 8/114 = 7.02% | 1/114 = 0.88% | 9/228 = 3.95% | 96 | 1 |
| AND | 208/456 = 45.61% | 104/114 = 91.23% | 0/114 = 0.00% | 104/228 = 45.61% | 1 | 96 |
| Always CoBEVT | 26/456 = 5.70% | 13/114 = 11.40% | 0/114 = 0.00% | 13/228 = 5.70% | 96 | 9 |

### 0002 — 288 queries, 144 positive, 144 negative, 576 agent labels

| Policy | Mean error | Joint FN | Joint FP | R2 | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|
| Local | 155/576 = 26.91% | 10/144 = 6.94% | 0/144 = 0.00% | 10/288 = 3.47% | 0 | 0 |
| Always Late Fusion | 22/576 = 3.82% | 10/144 = 6.94% | 1/144 = 0.69% | 11/288 = 3.82% | 134 | 1 |
| Disagreement Gate | 22/576 = 3.82% | 10/144 = 6.94% | 1/144 = 0.69% | 11/288 = 3.82% | 134 | 1 |
| OR | 22/576 = 3.82% | 10/144 = 6.94% | 1/144 = 0.69% | 11/288 = 3.82% | 134 | 1 |
| AND | 288/576 = 50.00% | 144/144 = 100.00% | 0/144 = 0.00% | 144/288 = 50.00% | 1 | 134 |
| Always CoBEVT | 22/576 = 3.82% | 11/144 = 7.64% | 0/144 = 0.00% | 11/288 = 3.82% | 136 | 3 |

### 0003 — 396 queries, 198 positive, 198 negative, 792 agent labels

| Policy | Mean error | Joint FN | Joint FP | R2 | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|
| Local | 168/792 = 21.21% | 23/198 = 11.62% | 0/198 = 0.00% | 23/396 = 5.81% | 0 | 0 |
| Always Late Fusion | 56/792 = 7.07% | 23/198 = 11.62% | 5/198 = 2.53% | 28/396 = 7.07% | 117 | 5 |
| Disagreement Gate | 56/792 = 7.07% | 23/198 = 11.62% | 5/198 = 2.53% | 28/396 = 7.07% | 117 | 5 |
| OR | 58/792 = 7.32% | 23/198 = 11.62% | 6/198 = 3.03% | 29/396 = 7.32% | 116 | 6 |
| AND | 278/792 = 35.10% | 139/198 = 70.20% | 0/198 = 0.00% | 139/396 = 35.10% | 6 | 116 |
| Always CoBEVT | 60/792 = 7.58% | 28/198 = 14.14% | 2/198 = 1.01% | 30/396 = 7.58% | 122 | 14 |

### 0004 — 360 queries, 180 positive, 180 negative, 720 agent labels

| Policy | Mean error | Joint FN | Joint FP | R2 | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|
| Local | 58/720 = 8.06% | 4/180 = 2.22% | 3/180 = 1.67% | 7/360 = 1.94% | 0 | 0 |
| Always Late Fusion | 44/720 = 6.11% | 4/180 = 2.22% | 18/180 = 10.00% | 22/360 = 6.11% | 29 | 15 |
| Disagreement Gate | 44/720 = 6.11% | 4/180 = 2.22% | 18/180 = 10.00% | 22/360 = 6.11% | 29 | 15 |
| OR | 44/720 = 6.11% | 4/180 = 2.22% | 18/180 = 10.00% | 22/360 = 6.11% | 29 | 15 |
| AND | 72/720 = 10.00% | 33/180 = 18.33% | 3/180 = 1.67% | 36/360 = 10.00% | 15 | 29 |
| Always CoBEVT | 86/720 = 11.94% | 27/180 = 15.00% | 16/180 = 8.89% | 43/360 = 11.94% | 23 | 51 |

### 0005 — 620 queries, 310 positive, 310 negative, 1240 agent labels

| Policy | Mean error | Joint FN | Joint FP | R2 | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|
| Local | 224/1240 = 18.06% | 19/310 = 6.13% | 3/310 = 0.97% | 22/620 = 3.55% | 0 | 0 |
| Always Late Fusion | 110/1240 = 8.87% | 19/310 = 6.13% | 36/310 = 11.61% | 55/620 = 8.87% | 147 | 33 |
| Disagreement Gate | 110/1240 = 8.87% | 19/310 = 6.13% | 36/310 = 11.61% | 55/620 = 8.87% | 147 | 33 |
| OR | 112/1240 = 9.03% | 19/310 = 6.13% | 37/310 = 11.94% | 56/620 = 9.03% | 146 | 34 |
| AND | 336/1240 = 27.10% | 165/310 = 53.23% | 3/310 = 0.97% | 168/620 = 27.10% | 34 | 146 |
| Always CoBEVT | 112/1240 = 9.03% | 43/310 = 13.87% | 13/310 = 4.19% | 56/620 = 9.03% | 157 | 45 |

### 0006 — 608 queries, 304 positive, 304 negative, 1216 agent labels

| Policy | Mean error | Joint FN | Joint FP | R2 | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|
| Local | 126/1216 = 10.36% | 17/304 = 5.59% | 7/304 = 2.30% | 24/608 = 3.95% | 0 | 0 |
| Always Late Fusion | 88/1216 = 7.24% | 17/304 = 5.59% | 27/304 = 8.88% | 44/608 = 7.24% | 58 | 20 |
| Disagreement Gate | 88/1216 = 7.24% | 17/304 = 5.59% | 27/304 = 8.88% | 44/608 = 7.24% | 58 | 20 |
| OR | 96/1216 = 7.89% | 17/304 = 5.59% | 31/304 = 10.20% | 48/608 = 7.89% | 54 | 24 |
| AND | 156/1216 = 12.83% | 71/304 = 23.36% | 7/304 = 2.30% | 78/608 = 12.83% | 24 | 54 |
| Always CoBEVT | 60/1216 = 4.93% | 21/304 = 6.91% | 9/304 = 2.96% | 30/608 = 4.93% | 91 | 25 |

### 0007 — 442 queries, 221 positive, 221 negative, 884 agent labels

| Policy | Mean error | Joint FN | Joint FP | R2 | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|
| Local | 200/884 = 22.62% | 4/221 = 1.81% | 0/221 = 0.00% | 4/442 = 0.90% | 0 | 0 |
| Always Late Fusion | 32/884 = 3.62% | 4/221 = 1.81% | 12/221 = 5.43% | 16/442 = 3.62% | 182 | 14 |
| Disagreement Gate | 28/884 = 3.17% | 4/221 = 1.81% | 10/221 = 4.52% | 14/442 = 3.17% | 182 | 10 |
| OR | 28/884 = 3.17% | 4/221 = 1.81% | 10/221 = 4.52% | 14/442 = 3.17% | 182 | 10 |
| AND | 372/884 = 42.08% | 186/221 = 84.16% | 0/221 = 0.00% | 186/442 = 42.08% | 10 | 182 |
| Always CoBEVT | 82/884 = 9.28% | 33/221 = 14.93% | 8/221 = 3.62% | 41/442 = 9.28% | 171 | 53 |

### 0008 — 750 queries, 375 positive, 375 negative, 1500 agent labels

| Policy | Mean error | Joint FN | Joint FP | R2 | Corrected | Introduced |
|---|---:|---:|---:|---:|---:|---:|
| Local | 34/1500 = 2.27% | 2/375 = 0.53% | 1/375 = 0.27% | 3/750 = 0.40% | 0 | 0 |
| Always Late Fusion | 6/1500 = 0.40% | 2/375 = 0.53% | 1/375 = 0.27% | 3/750 = 0.40% | 28 | 0 |
| Disagreement Gate | 6/1500 = 0.40% | 2/375 = 0.53% | 1/375 = 0.27% | 3/750 = 0.40% | 28 | 0 |
| OR | 8/1500 = 0.53% | 2/375 = 0.53% | 2/375 = 0.53% | 4/750 = 0.53% | 27 | 1 |
| AND | 60/1500 = 4.00% | 29/375 = 7.73% | 1/375 = 0.27% | 30/750 = 4.00% | 1 | 27 |
| Always CoBEVT | 80/1500 = 5.33% | 39/375 = 10.40% | 1/375 = 0.27% | 40/750 = 5.33% | 23 | 69 |

Full machine-readable rows are in `per_sequence_policy.csv`. The seven gate-versus-OR events are in `gate_or_differences.csv`.
