# Expert reliability calibration

Section 4.3 and Figure 11 vary Agent A's true error and the error rate declared to the fuser. B and C stay at 0.26 and 0.32, with an 18% common shock. The grid is the original one: true error 0.015, 0.05, 0.10, 0.20, 0.30, 0.40, and 0.45; assumed error 0.003, 0.006, 0.010, 0.015, 0.020, 0.030, 0.045, 0.060, and 0.100. There are 63 cells.

The generator, conservative F0, and expert override are the original functions in `scripts/run_three_agent_tradeoff_frontier.py`. The run uses 2,000 frames, 2 queries per frame, and seed `77109`, so every policy and every true-error setting shares the same latent uniforms. Assumed error changes only the reliability table passed to the fuser. It does not change the local predictions. Always-A broadcasts A's observed label to all three agents. That baseline is scored here; it is not a new branch of the original fuser.

Paired frame bootstrap: 2,000 resamples, seed `77109+123`, both queries kept together. Six additional seeds, `77109` through `77114`, repeat the two headline cells.

## Matched reliability, true and assumed error 1.5%

| Policy | Mean error | R2 | R3 |
|---|---:|---:|---:|
| Local | 2,403/12,000 = 20.025% | 792/4,000 = 19.800% | 8/4,000 = 0.200% |
| Conservative F0 | 1,639/12,000 = 13.658% | 792/4,000 = 19.800% | 16/4,000 = 0.400% |
| Expert override | 165/12,000 = 1.375% | 55/4,000 = 1.375% | 55/4,000 = 1.375% |
| Always-A | 165/12,000 = 1.375% | 55/4,000 = 1.375% | 55/4,000 = 1.375% |

The override and Always-A are the same 55 queries. Against local, R2 changes by −18.425 percentage points, interval [−19.651, −17.150], and R3 by +1.175 points, interval [+0.875, +1.525]. These are the Section 4.3 figures. Conservative F0 leaves R2 unchanged and lowers mean error by 6.367 points, interval [−6.775, −5.950]. Its R3 change is +0.200 points, interval [+0.075, +0.350].

## Overstated reliability, true error 45% and assumed error 1.5%

| Policy | Mean error | R2 | R3 |
|---|---:|---:|---:|
| Local | 4,158/12,000 = 34.650% | 1,140/4,000 = 28.500% | 338/4,000 = 8.450% |
| Conservative F0 | 4,090/12,000 = 34.083% | 1,140/4,000 = 28.500% | 694/4,000 = 17.350% |
| Expert override | 5,430/12,000 = 45.250% | 1,810/4,000 = 45.250% | 1,810/4,000 = 45.250% |
| Always-A | 5,430/12,000 = 45.250% | 1,810/4,000 = 45.250% | 1,810/4,000 = 45.250% |

The override again equals Always-A. Relative to local, R2 rises by 16.750 points, interval [+14.900, +18.675], and R3 by 36.800 points, interval [+35.325, +38.325]. The manuscript states 16.75 and 36.80. Mean error rises by 10.600 points, interval [+9.308, +11.934]. Conservative F0 still does not change R2. It lowers mean error by 0.567 points and raises R3 by 8.900 points, interval [+7.975, +9.750].

Figure 11 is `fig4_expert_calibration.pdf`. The cross marks true and assumed error both equal to 1.5%. Blue is a lower risk than local. Red is a higher risk.

## When trusting A becomes harmful

The override fires only when its assumed error is 0.3%, 0.6%, 1.0%, or 1.5%. On all 28 of those cells, and for every true error in the grid, it copies A onto all three agents. At an assumed error of 2% or higher, the solo confidence of A falls below 0.90, the override does not fire, and the result is identical to conservative F0. That is the sharp guard described in Section 4.3. It is a property of this fixed B/C weighting, not a universal threshold at 2%.

On the 28 cells where the override fires:

- R3 is higher than local at every true error, including 1.5%. Broadcasting A turns each of A's mistakes into an all-three mistake. At 1.5% the increase is 1.175 points. At 45% it is 36.800 points.
- R2 is lower than local at true error 1.5%, 5%, 10%, and 20%. It is higher at 30%, 40%, and 45%, by 5.100, 13.100, and 16.750 points.
- Mean error is still lower at 20% (−5.933 points) and higher from 30% upward (+0.667, +7.583, and +10.600 points).

So a declared error of 1.5% is already harmful for all-three failure when A is actually reliable, and it becomes harmful for majority failure and mean error once A's true error reaches 30% on this draw. Raising the declared error to 2% removes the single-agent override. It does not remove conservative F0's own R3 increase, which comes from sharing a wrong majority rather than from trusting A alone.

Conservative F0's R2 difference from local is 0 on all 63 cells. Its mean error and R3 do move with the declared error, but on this grid that movement appears at the 10% declaration, where A is down-weighted. Even there, R2 remains equal to local.

Across seeds `77109`–`77114`, with assumed error held at 1.5%, the override-minus-local signs do not change. At true error 1.5%, R2 changes lie in [−20.25, −17.45] points and R3 changes lie in [+1.000, +1.425]. At true error 45%, R2 changes lie in [+13.700, +18.025] and R3 changes lie in [+33.925, +37.000]. On every one of those seeds the override equals Always-A, and conservative F0's R2 difference remains 0.
