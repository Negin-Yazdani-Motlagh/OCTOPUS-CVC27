# Remaining controlled-mechanism checks

Three checks close the partial P1 items. All use 2,000 frames and 2 queries per frame. The six seeds are `5701` through `5706`. Policies on one seed share the latent draws. The frame bootstrap has 2,500 replicates and seed `seed+109`. Truth is used only for scoring. The original source was not edited. Seed `5701` at correlation 0.75 reproduces the earlier five-agent counts exactly.

## Six seeds of the five-agent correlation study

The generator and fuser are `generate_controlled_traces` and `fast_study_run` in `Octopus-main/scripts/run_f0_cvc_parameter_study.py`. Agents a and b remain independent at 0.055 and 0.080. Agents c, d, and e have error 0.18 and share one error draw with probability ρ = 0.75. Each agent still has its own result ID. Correct grouping puts c, d, and e in one group. Incorrect grouping gives every agent its own group.

On seed `5701`, 4,000 queries and 20,000 labels:

| Policy | Mean error | R3 | R5 |
|---|---:|---:|---:|
| Local | 2,743/20,000 = 13.715% | 581/4,000 = 14.525% | 2/4,000 = 0.050% |
| Majority broadcast | 2,905/20,000 = 14.525% | 581/4,000 = 14.525% | 581/4,000 = 14.525% |
| Weighted broadcast | 495/20,000 = 2.475% | 99/4,000 = 2.475% | 99/4,000 = 2.475% |
| Correctly grouped F0 | 854/20,000 = 4.270% | 99/4,000 = 2.475% | 11/4,000 = 0.275% |
| Incorrectly grouped F0 | 2,011/20,000 = 10.055% | 581/4,000 = 14.525% | 80/4,000 = 2.000% |

The grouped-minus-local intervals on this seed are R3 −12.050 points [−13.075, −11.050] and R5 +0.225 points [+0.100, +0.400]. Those are the previously saved intervals.

Across the six seeds, the paired changes versus local at ρ = 0.75 stay in these ranges:

| Policy | Mean error | R3 | R5 |
|---|---:|---:|---:|
| Majority broadcast | +0.205 to +0.810 | 0 | +13.375 to +14.800 |
| Weighted broadcast | −11.555 to −10.650 | −12.300 to −10.875 | +2.400 to +2.650 |
| Correctly grouped F0 | −9.645 to −8.830 | −12.300 to −10.875 | +0.225 to +0.525 |
| Incorrectly grouped F0 | −4.035 to −3.660 | 0 | +1.600 to +2.025 |

Every within-seed interval for the grouped and weighted R3 decrease excludes 0, and every interval for their R5 increase excludes 0. Incorrect grouping leaves R3 exactly equal to local on every seed. Weighted broadcast has lower mean error than grouped F0 on every seed, and higher R5, because it has no fallback. Majority broadcast does not lower mean error here: the correlated trio can outvote a and b, so its R3 and R5 equal the local R3.

## Equal true and assumed error 0.10

Every agent is drawn independently with error 0.10, and F0 is told 0.10 for every agent. A split whose weights differ by one copy of `log(0.9/0.1)` has confidence 0.8999999999999999, which is below the 0.90 gate. Equal-weight 2–1 and 3–2 votes are therefore not accepted. A 4–1 or unanimous vote clears the gate.

On seed `5701`:

| Study | Policy | Mean error | Collective risk |
|---|---|---:|---:|
| Three agents | Local | 1,189/12,000 = 9.908% | R2 111/4,000 = 2.775%, R3 7/4,000 = 0.175% |
| Three agents | Majority and weighted | 333/12,000 = 2.775% | R2 = R3 = 111/4,000 = 2.775% |
| Three agents | F0, any grouping below | 1,189/12,000 = 9.908% | same as local |
| Five agents | Local | 1,978/20,000 = 9.890% | R3 39/4,000 = 0.975%, R5 0/4,000 |
| Five agents | Majority and weighted | 195/20,000 = 0.975% | R3 = R5 = 39/4,000 = 0.975% |
| Five agents | F0, one group per agent | 649/20,000 = 3.245% | R3 39/4,000 = 0.975%, R5 2/4,000 = 0.050% |
| Five agents | F0, false clique on c, d, e | 1,007/20,000 = 5.035% | R3 39/4,000 = 0.975%, R5 8/4,000 = 0.200% |
| Five agents | F0, all five in one group | 1,978/20,000 = 9.890% | same as local |

Weighted broadcast matches majority on every label, because equal error rates give equal weights. On all six seeds, three-agent F0 matches local exactly for independent groups, for a false pair, and for one shared group. The only non-unanimous split is 2–1, and that split fails the 0.90 gate. Majority is the rule that changes labels: its mean-error decrease versus local lies in −7.383 to −6.942 points, its R2 change is 0, and its R3 increase lies in +2.600 to +2.925 points.

Five-agent F0 with one group per agent does change labels, but only on 4–1 and unanimous queries. Its R3 change is 0 on every seed. Mean error falls by 6.380 to 6.740 points, and R5 rises by 0.025 to 0.050 points. Declaring an independent trio to be one clique is worse on both of those changes: mean error falls by only 4.635 to 5.025 points, and R5 rises by 0.175 to 0.325 points. Putting all five in one group never has two supporting groups, so it matches local on every label. Majority still has the lowest mean error, −8.915 to −9.410 points, and the highest R5, +0.750 to +0.975 points.

## Shared result IDs versus correlated errors

Correlation 0.75 gives c, d, and e distinct result IDs and a shared error bit on only some queries. On seed `5701` their three predictions match on 3,560/4,000 queries (89.00%). Across seeds that rate is 87.95% to 89.60%. At correlation 0 the same agents match on 2,200/4,000 to 2,266/4,000 queries, about 55% to 57%. At correlation 1 they match on 4,000/4,000 queries. That last case is an exact copy of one error draw, still stored under three result IDs.

Giving those three identical predictions one shared result ID, and the correct single group, produces the same F0 decision on every query and every seed as the distinct IDs with that same group. The result-ID string does not add a second vote. Assigning the shared ID to three different dependence groups is rejected. Both attempted observations raise `Same physical result cannot claim independent dependence groups`.

On the exact-copy queries, seed `5701`:

| Policy | Mean error | R3 | R5 |
|---|---:|---:|---:|
| Local | 2,682/20,000 = 13.410% | 720/4,000 = 18.000% | 3/4,000 = 0.075% |
| Majority broadcast | 3,600/20,000 = 18.000% | 720/4,000 = 18.000% | 720/4,000 = 18.000% |
| Weighted broadcast | 500/20,000 = 2.500% | 100/4,000 = 2.500% | 100/4,000 = 2.500% |
| F0, correct group or shared result ID | 822/20,000 = 4.110% | 100/4,000 = 2.500% | 11/4,000 = 0.275% |
| F0, distinct IDs and incorrect groups | 2,360/20,000 = 11.800% | 720/4,000 = 18.000% | 92/4,000 = 2.300% |

Across the six seeds, correct grouping and the shared result ID have the same paired changes: mean error −9.720 to −8.805 points, R3 −16.200 to −14.675, and R5 +0.200 to +0.475. Incorrect grouping of the distinct copied IDs leaves R3 unchanged and raises R5 by 2.075 to 2.500 points. Majority broadcast, which counts the copied prediction three times, raises mean error by 4.260 to 4.960 points and raises R5 by 17.350 to 19.075 points.

The environmental case is different because the trio can disagree. At correlation 0.75, correct grouping lowers R3 by 10.875 to 12.300 points. Incorrect grouping does not. At correlation 0, where agreement is only a little above chance, correct grouping lowers mean error by 8.835 to 9.670 points but its R3 change is only −0.475 to 0 points. A shared result ID is not that partial agreement. It is one artifact, one prediction within the query, and one legal dependence group.
