# P1 five-agent dependence reproduction

Section 4.4 and Figure 8 come from `Octopus-main/scripts/run_f0_cvc_parameter_study.py`. The command was:

```bash
python scripts/run_f0_cvc_parameter_study.py \
  --output Negin_validation/P1/five_agent \
  --frames 2000 --rois 2 --seed 5701 \
  --bootstrap 2500 --online-check-frames 180 --skip-v2v
```

`--skip-v2v` is an existing flag. The script's extra sequence-0007 replay looks for `examples/v2v4real_real_seq0007/trace.jsonl`, which is not in this tree. That replay is not part of Section 4.4 or Figure 8. The original source was not modified.

## Configuration

There are 2,000 frames and 2 queries per frame, so 4,000 queries and 20,000 agent labels. Seed `5701`. Agents a and b are independent, with error probabilities 0.055 and 0.080. Agents c, d, and e each have error probability 0.18. With probability ρ they share one Bernoulli(0.18) error draw; otherwise those three draws are independent. ρ is the mixture weight. The sweep is 0, 0.25, 0.50, 0.75, and 1. The same latent uniforms are reused across ρ and across policies. The group declaration is supplied even at ρ = 0. It is not estimated from the outcomes.

Conservative F0 uses confidence 0.90, two supporting groups, two independent groups, conflict fraction at most 0.40, and dependence discount 1. Correct grouping is `(a)`, `(b)`, `(c,d,e)`. Incorrect grouping gives c, d, and e three separate groups. Weighted broadcast applies `log((1-q)/q)` to every agent and shares that label on every query. Truth is used only for scoring.

The bootstrap resamples 2,000 physical frames, both queries together, for 2,500 draws. The resample seed is `5701+109`. Intervals are pointwise 95% percentiles, not a simultaneous band over the sweep.

## Results at ρ = 0.75

| Policy | Mean error | R3 | R5 |
|---|---:|---:|---:|
| Local | 2,743/20,000 = 13.715% | 581/4,000 = 14.525% | 2/4,000 = 0.050% |
| Weighted broadcast | 495/20,000 = 2.475% | 99/4,000 = 2.475% | 99/4,000 = 2.475% |
| Correctly grouped F0 | 854/20,000 = 4.270% | 99/4,000 = 2.475% | 11/4,000 = 0.275% |
| Incorrectly grouped F0 | 2,011/20,000 = 10.055% | 581/4,000 = 14.525% | 80/4,000 = 2.000% |

Pointwise frame-bootstrap intervals at this setting:

| Policy | R3 interval | R5 interval |
|---|---:|---:|
| Local | [13.500, 15.600] | [0.000, 0.125] |
| Weighted broadcast | [2.012, 2.975] | [2.012, 2.975] |
| Correctly grouped F0 | [2.012, 2.975] | [0.125, 0.450] |
| Incorrectly grouped F0 | [13.500, 15.600] | [1.575, 2.425] |

Paired change versus local, the contrast quoted in Section 4.4:

| Contrast | R3 | R5 |
|---|---:|---:|
| Grouped F0 − local | −12.050 pp [−13.075, −11.050] | +0.225 pp [+0.100, +0.400] |
| Weighted broadcast − local | −12.050 pp [−13.075, −11.050] | +2.425 pp [+1.975, +2.900] |
| Ungrouped F0 − local | 0 pp [0, 0] | +1.950 pp [+1.525, +2.375] |

The manuscript prints local 14.53% and 0.05%, grouped F0 2.48% and 0.28%, ungrouped F0 14.53% and 2.00%, and weighted broadcast 2.48% and 2.48%. It prints the grouped-minus-local intervals as [−13.08, −11.05] and [+0.10, +0.40]. Those are the rates and intervals above, rounded to two decimals. The study note's unrounded values, 14.525%, 2.475%, 0.275%, −12.050, [−13.075, −11.050], and [+0.100, +0.400], match this run exactly.

## The other mixture weights

Mean error stays near the designed marginal rate for local, about 13.4% to 13.8%, at every ρ. R3 and R5, in percent:

| ρ | Local R3, R5 | Weighted R3 = R5 | Grouped R3, R5 | Ungrouped R3, R5 |
|---:|---:|---:|---:|---:|
| 0.00 | 1.825, 0.000 | 1.375 | 1.375, 0.275 | 1.825, 0.200 |
| 0.25 | 5.875, 0.000 | 1.750 | 1.750, 0.275 | 5.875, 0.825 |
| 0.50 | 10.450, 0.025 | 2.075 | 2.075, 0.275 | 10.450, 1.350 |
| 0.75 | 14.525, 0.050 | 2.475 | 2.475, 0.275 | 14.525, 2.000 |
| 1.00 | 18.000, 0.075 | 2.500 | 2.500, 0.275 | 18.000, 2.300 |

Grouped F0 and weighted broadcast have the same R3 at every ρ. Grouped R5 stays 11/4,000. Ungrouped R3 equals local R3 at every ρ, including the paired difference of exactly zero at ρ = 0.75. Local R5 is an observed zero at ρ = 0 and 0.25. As the manuscript says, a zero count is not evidence that the probability is zero. Figure 8 plots that zero.

`fig_five_agent_lineage.pdf` is the manuscript figure: Local, Weighted broadcast, Grouped F0, and Ungrouped F0, with linear axes. The script's own `02_lineage_quality_vs_correlation.pdf` is a different chart. It draws naive majority instead of weighted broadcast and uses a logarithmic R5 axis.

## Why a separate group for each clique member changes the result

F0 keeps one vote per declared group. The vote uses the largest assumed error in the group, so three clique members declared together contribute one weight, `log(0.82/0.18) ≈ 1.52`. A and b remain separate, with weights about 2.84 and 2.44. When a and b agree, their combined weight is about 5.29. That beats the single clique vote by enough to pass confidence 0.90, so grouped F0 can share the a/b label and correct the clique. If the guards fail, each agent keeps its own label. A wrong clique therefore does not automatically overwrite a and b, which is why grouped R5 stays at 0.275% while local R5 is 0.050%. Sharing still creates some all-five errors; it does not remove them.

Declaring c, d, and e independent gives the clique three copies of the 1.52 weight, about 4.55. Against a unanimous a and b, the margin falls to about 0.74 and the confidence falls below 0.90, so F0 keeps the local labels. The three clique errors remain, and R3 stays equal to local. The separate copies do clear 0.90 when the clique is joined by one of a or b. F0 then overwrites the remaining correct agent. That turns a four-agent error into a five-agent error and is why ungrouped R5 rises to 2.000% without any change in R3.

Weighted broadcast has no fallback. Its label is given to all five agents, so its R3 and R5 are the same number. At ρ = 0.75 that number equals grouped F0's R3, 2.475%, but its R5 is 2.475% rather than 0.275%, and its mean error is lower, 2.475% versus 4.270%. The lower mean error is the errors corrected by always sharing. Grouped F0 gives up some of those corrections when it falls back, and that fallback is what keeps most correct local labels from being overwritten.

The first 180 frames were also run through the simulator for these policies. The offline labels matched the executed predictions. Energy in the study files is the hypothetical profile, not a measurement.
