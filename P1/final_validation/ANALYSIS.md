# Final P1 validation

The original fuser and the earlier result folders were left unchanged. The alternate confidence rule exists only in `threshold_stability.py`. New tests are in this folder, not in `Octopus-main/tests`.

## Confidence boundary

A one-weight margin at error 0.10 has logit `log(9) = 2.1972245773362196`. The sigmoid of that value is `0.8999999999999999`, which fails `confidence < 0.90`. The fuser’s own weight, `log1p(-0.10) - log(0.10)`, is `4.44e-16` below `log(9)`, so a strict comparison with the logit boundary rejects the same case.

The validation gate accepts when `abs(logit) + 1e-12 >= log(t / (1 - t))`. The same `1e-12` tolerance on the probability also accepts this boundary and still rejects a score 0.01 nats below it. On seeds `5701`–`5706`, 2,000 frames and 2 queries, with every agent at true and assumed error 0.10:

| Agents | Original float gate | Logit boundary, tolerance `1e-12` |
|---|---|---|
| 3 | Same labels as local. Seed `5701`: 1,189/12,000 = 9.908% mean, R2 111/4,000, R3 7/4,000 | Same labels as majority on every seed. Seed `5701`: 333/12,000 = 2.775%, R2 = R3 = 111/4,000 |
| 5 | Seed `5701`: 649/20,000 = 3.245% mean, R3 39/4,000, R5 2/4,000 | Same labels as majority on every seed. Seed `5701`: 195/20,000 = 0.975%, R3 = R5 = 39/4,000 |

The tolerance therefore turns equal-reliability F0 into majority broadcast. R2 stays at the local rate for three agents. For five agents, R5 rises from 1 or 2 queries to the full majority-wrong count, 30 to 39 queries out of 4,000.

The same tolerance changes 0 of 4,000 decisions on the published heterogeneous draws: three-agent Table 3, seed `77109`, shock 0.18, and five-agent Figure 8, seed `5701`, ρ = 0.75, with either the correct clique group or five separate groups.

## Tests

The upstream suite, run from `Octopus-main` with the validation environment, finished as 325 passed, 1 skipped, 23 failed, in 33.04 seconds. The skip is the capture-contract test, which requires torch. Every recorded failure is a `FileNotFoundError` for a pinned input that is not in this tree: `examples/v2v4real_real_seq0007/trace.jsonl`, `empirical/v2v4real/sequence_counts.csv`, `empirical/v2v4real/packed_outcomes.json`, or the CooperScene CSV. The log is `upstream_pytest.txt`.

`test_regressions.py` adds five checks and passes 5/5:

- the float gate rejects the equal-weight margin, and the `1e-12` logit gate accepts it
- a score 0.01 nats below the boundary stays rejected
- flipping the stored truth changes the scored labels and leaves the fusion actions unchanged
- one result ID cannot claim two groups or two predictions; one shared ID with one group matches distinct IDs with that same group
- a 21 ms deadline still runs the edge job and returns every local prediction, with total energy equal to baseline plus incremental

## Synthetic 3,000-event E1

`evaluate_dataset` from `scripts/run_e1_multiobjective.py` was called on `examples/energy/three_agent_per_bit.json` with 3,000 events, 3,000 bootstrap replicates, block length 1, and seed `711911`. That is the seed the original `main` assigns to the synthetic dataset when the 0007 replay is index 0. The 0007 replay was not repeated. The point estimates match `docs/MULTI_OBJECTIVE_E1.md`:

| Shared late fusion | All three wrong | Mean error | Incremental J/event | Mean latency |
|---|---:|---:|---:|---:|
| 0% | 40/3,000 = 1.333% | 9.933% | 0.2400 | 20.000 ms |
| 25% | 2.667% | 9.044% | 0.2664 | 24.672 ms |
| 50% | 3.767% | 8.044% | 0.2923 | 29.238 ms |
| 75% | 4.467% | 6.800% | 0.3186 | 33.892 ms |
| 100% | 5.367% | 5.367% | 0.3448 | 38.514 ms |

Idle baseline is 32,694.55 J on every row, 10.898 J/event. It does not depend on the cooperation rate. Incremental energy is the column above.

## Deadline and packet loss

The six-seed grid was executed again with the original three-agent generator, seeds `77109`–`77114`, shock 0.18, 600 frames, and 2 queries. Previous `execution_robustness` files were not rewritten. Incremental joules for seed `77109` match that earlier table: local 144.000 J (0.24000 J/frame), conservative F0 154.644 J (0.25774 J/frame), expert override 154.653 J (0.25776 J/frame), and both fusion policies 149.014 J (0.24836 J/frame) at 100% loss.

Idle baseline is the same for local, conservative F0, and the expert override. It does not depend on the seed or the packet-loss rate. It does depend on the deadline, because the ledger’s horizon is the last frame release plus the deadline. At 21 ms the baseline is 2,285.643 J (3.809 J/frame). At 150 ms it is 2,288.455 J (3.814 J/frame). The 2.812 J difference is 129 ms times 21.8 W, the sum of three vehicle baselines at 1.6 W and the edge baseline at 17 W.

Within a seed, incremental joules do not change across the deadline list. Across seeds, conservative F0 incremental energy at zero loss varies from 154.641 J to 154.646 J, because the number of accepted downlinks changes the radio cost. Local and expert totals do not vary by seed. At a 21 ms deadline, 0.009399 J of fusion work falls after the horizon and is reported as post-window energy. It is already included in the incremental total. From 31.5 ms onward that post-window term is 0. Lost uploads are not refunded: at 100% loss the incremental total remains 149.014 J, above the local 144.000 J, with 0 edge jobs and 3,686,400 transmitted bytes.
