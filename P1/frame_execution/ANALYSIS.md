# Sequence 0007 frame-level cooperation

Section 5 and Figure 9 replay the recorded sequence 0007 under the original E1 resource configuration. Each of the 221 physical frames is assigned local-only processing or cooperative late fusion with target probability 0%, 25%, 50%, 75%, or 100%. The coin is tossed once per frame, using seed `20261118`. Both local detectors still run when fusion is selected. The trace is the regenerated sequence 0007 extracted from `Negin_validation/P0/v2v4real_all/trace.jsonl`: 221 frames and 442 queries. The nine-sequence arrival offset was removed so these frames occupy slots 0 through 220. The original simulator and configuration files were not edited.

There are 884 agent labels (442 queries × 2 vehicles). Mean error is wrong labels over 884. R2 is queries on which both vehicles are wrong, over 442. Energy is modeled incremental joules divided by 221 physical frames. The vertical intervals are a circular moving-block bootstrap of 12 consecutive frames, 3,000 resamples, seed `711910`. They describe this one sequence. The horizontal ranges are the minimum and maximum of nine hypothetical radio and fusion-power multipliers. They are not confidence intervals. No deadline was missed, and every query received both labels.

## Frame-level results

| Target | Frames fused | Mean error | R2 | Energy (J/frame) | Detector runs | Edge jobs | Bytes |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0% | 0/221 | 200/884 = 22.624% | 4/442 = 0.905% | 0.160 | 442 | 0 | 0 |
| 25% | 52/221 | 154/884 = 17.421% | 4/442 = 0.905% | 0.180 | 442 | 52 | 439,296 |
| 50% | 107/221 | 111/884 = 12.557% | 6/442 = 1.357% | 0.200 | 442 | 107 | 903,936 |
| 75% | 162/221 | 72/884 = 8.145% | 10/442 = 2.262% | 0.221 | 442 | 162 | 1,368,576 |
| 100% | 221/221 | 32/884 = 3.620% | 16/442 = 3.620% | 0.243 | 442 | 221 | 1,867,008 |

The manuscript reports the same endpoints: mean error falls from 22.62% to 3.62%, joint error rises from 0.90% to 3.62%, and modeled energy rises from 0.160 to 0.243 J/frame. At the 25% target, the joint-error count stays at 4 and mean error is 17.42%, as stated in Section 5. The methods table’s per-decision energies, 0.0800, 0.0898, 0.1002, 0.1106, and 0.1217 J, are these frame energies divided by two. Mean delivered latency is 20.000, 23.844, 27.911, 31.977, and 36.339 ms. Figure 9 is `fig_real_energy_tradeoff.pdf`.

The 12-frame bootstrap intervals, in percentage points, are:

| Target | Mean error | R2 |
|---|---|---|
| 0% | [21.041, 24.095] | [0.226, 1.810] |
| 25% | [15.724, 19.118] | [0.226, 1.810] |
| 50% | [10.520, 14.480] | [0.452, 2.489] |
| 75% | [6.222, 10.181] | [1.131, 3.394] |
| 100% | [2.262, 4.977] | [2.262, 4.977] |

At 0% the energy range is a single point, 0.160 J/frame, because no radio or fusion work occurs. At 100% the nine profiles span 0.199 to 0.350 J/frame around the nominal 0.243. Lengthening the block from 12 to 24 frames moves the lower end of the four-event joint rate to 0 at both 0% and 25%. The unchanged count of four therefore does not show that joint risk stays constant in expectation. That is the limitation stated in Section 5.

## Computation is charged once per physical frame

Frame execution builds 221 batches. Each batch serves both queries. Local-only execution runs 442 detectors, two vehicles times 221 frames, and records 442 projection-cache hits: the second query reads the artifact already produced for that frame. Full cooperation adds 221 edge jobs and 1,867,008 bytes, which is 8,448 bytes for each cooperating frame. Incremental energy is 35.360 J at 0% and 53.793 J at 100%.

The same trace with decision granularity builds 442 batches, one per query. The endpoints then charge 884 detector runs, 442 edge jobs, 3,734,016 bytes, and twice the incremental energy: 70.720 J and 107.586 J. The error endpoints do not change, because every query is local at 0% and every query receives the recorded late-fusion label at 100%. The intermediate targets do change. A per-query coin at the 25% target fuses 104 of 442 queries, leaves 6 joint errors rather than 4, and raises mean error to 161/884 = 18.213%. The frame-level replay is the one that matches Section 5.
