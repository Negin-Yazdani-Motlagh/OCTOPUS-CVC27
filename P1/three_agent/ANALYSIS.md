# P1 three-agent reproduction

Section 4.3 of the manuscript and `docs/F0_THREE_AGENT_EXTENDED_METHODS.md` describe one synthetic experiment. The runner is `Octopus-main/scripts/run_three_agent_tradeoff_frontier.py`. It was executed unchanged:

```bash
python scripts/run_three_agent_tradeoff_frontier.py \
  --output Negin_validation/P1/three_agent \
  --frames 2000 --rois 2 --online-frames 600 \
  --seed 77109 --bootstrap 2000
```

## Configuration

There are 2,000 frames and 2 binary queries per frame, so 4,000 queries. Seed `77109`. Observer A has error probability 0.015. B and C have 0.26 and 0.32. A shared environmental shock hits B and C with probability `s`, while their marginal error rates stay fixed. A is independent of that shock. The shock grid is 0, 0.06, 0.12, 0.18, and 0.24. Table 3 uses `s = 0.18`.

The four policies are:

- Local: keep the three local labels.
- Majority broadcast: give every agent the unweighted majority label on every query.
- Conservative F0: unchanged `SelectiveFuser`, with two independent groups, two supporting groups, confidence 0.90, conflict fraction at most 0.40, source-error mask 0.49, and dependence discount 1.
- Expert override: a study-script rule. It shares the weighted winner only when strict F0's sole rejection is `insufficient_independent_support_for_winner`, the only supporter is predeclared expert A, and A's assumed error is at most 0.05. It does not change core F0.

Truth is used only after the decision. Assumed error rates are the configured table, not the event outcome. Paired frame bootstrap: 2,000 resamples, seed `77109+123` for the policy differences.

## Table 3 at s = 0.18

| Policy | R2 | R3 | Mean error | Acceptance |
|---|---:|---:|---:|---:|
| Local | 792/4,000 = 19.800% | 8/4,000 = 0.200% | 2,403/12,000 = 20.025% | 0/4,000 |
| Majority broadcast | 792/4,000 = 19.800% | 792/4,000 = 19.800% | 2,376/12,000 = 19.800% | 4,000/4,000 |
| Conservative F0 | 792/4,000 = 19.800% | 16/4,000 = 0.400% | 1,639/12,000 = 13.658% | 3,185/4,000 = 79.625% |
| Expert override | 55/4,000 = 1.375% | 55/4,000 = 1.375% | 165/12,000 = 1.375% | 4,000/4,000 |

The manuscript prints 20.03%, 13.66%, and 1.38%. Those are the same rates rounded to two decimals. R2 and R3 match the printed table exactly at that precision.

Conservative F0 lowers mean error by 6.367 percentage points and leaves R2 unchanged. Its R3 is 0.400%, against 19.800% for majority broadcast. The expert override changes R2 by −18.425 percentage points and R3 by +1.175 percentage points. The manuscript rounds those changes to 6.37, −19.65 to −17.15, and +0.88 to +1.53. The regenerated intervals are [−19.651, −17.150] and [+0.875, +1.525].

On this seed the override copies A's label onto all three agents for all 4,000 queries. A is wrong on 55 queries, which is the 1.375% rate. The override is therefore the always-A baseline in this favorable setting, as Section 4.3 states.

## Figure 7

`fig3_three_agent_risk_tradeoff.pdf` uses the manuscript renderer in `figure_reproduction/make_figures.py`: R2 and R3 against the B/C shock, for the same four policies. `01_majority_recovery_vs_shared_failure.pdf` is the study script's version of that figure and adds pointwise frame-bootstrap bars. The plotted rates are the rows of `shock_and_policy_grid.csv`.

At every shock, local, majority, and conservative F0 have the same R2. Majority's R3 equals that R2. Expert R2 and R3 stay at 1.375% because A does not depend on the shock and the override broadcasts A. Six seeds, `77109` through `77114`, keep the expert-minus-local signs: R2 changes lie in [−20.25, −17.45] percentage points and R3 changes lie in [+1.000, +1.425].

## Discrepancies

No count disagrees with Table 3 or with the intervals in Section 4.3 after the manuscript's two-decimal rounding. The study figure and the manuscript figure use the same grid and different annotations: the study figure draws bootstrap bars and calls majority "Majority broadcast"; the manuscript figure draws the lines only and calls it "Majority sharing."

The same command also wrote the calibration, deadline, and ROI-cost grids. Those are Figures 10–12 in the reproduction map, not Table 3 or Figure 7. Energy remains hypothetical.
