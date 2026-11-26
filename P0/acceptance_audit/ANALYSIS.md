# P0 acceptance additions

The tables use the regenerated trace in `P0/v2v4real_all/`. The original converter and the earlier CSVs were not changed.

A paired outcome compares the two local labels with one broadcast label on the same query. `both_success` means the locals are not jointly wrong and the broadcast is correct. `rescued_joint_failure` means both locals are wrong and the broadcast is correct. `introduced_joint_failure` means at least one local is correct and the broadcast is wrong. `both_fail` means both locals and the broadcast are wrong. Sequence 0007 under late fusion is 426, 0, 12, and 4. That is the count checked by `tests/test_cvc_figure_study.py`.

Late fusion rescues 0 joint failures in every sequence. Its 89 introduced failures are all negative queries. The 105 shared failures are the same 105 queries on which both local detectors are already wrong. All 1,993 frames contain both queries. Late fusion is correct on both queries of 1,808 frames.

Always-ego gives both agents the ego label. Always-partner gives both the partner label. Neither can rescue a joint failure, because the privileged detector is one of the two locals. Pooled always-ego error is 1,340/7,972 = 16.81%, and its R2 is 670/3,986 = 16.81%. Always-partner is 962/7,972 = 12.07% mean error and 481/3,986 = 12.07% R2. Local mean error is 14.44% and local R2 is 2.63%. Broadcasting either source therefore raises joint error. Late fusion remains lower than both, at 4.87% mean error and 4.87% R2. CoBEVT is the only listed broadcast that rescues joint failures: 35 queries, of which 29 are positive.

The bootstrap uses 20,000 replicates and seed `20261118`. The sequence-cluster draw matches the earlier late-fusion-minus-local intervals: mean error [−15.272, −5.248] percentage points and R2 [+0.882, +3.613]. The within-sequence design keeps every sequence, resamples its frames with a circular moving block, and keeps the two queries in a frame together. At block lengths 1, 6, 12, and 24, the pooled late-fusion-minus-local intervals still exclude 0. The 24-frame mean-error interval is [−10.273, −8.881] percentage points, much narrower than the sequence-cluster interval because the scenes are not redrawn.

Inside one sequence the picture is weaker. At a 12-frame block, sequences 0000, 0001, and 0002 have R2 intervals that include 0, and 0008 is exactly 0. Sequence 0004’s mean-error interval touches 0 at 12 frames and crosses above 0 at 24 frames, [−3.750, +0.139]. These within-sequence intervals do not replace the nine-scene interval.
