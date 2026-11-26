# Frame-level F0 execution

Figures 10 and 12 use the original three-agent executor: 600 frames, seed `77109`, shock 0.18, and hypothetical E1 energy. Local, conservative F0, and the expert override see the same local predictions. A second draw, six seeds `77109`–`77114`, changes deadline and packet loss separately. No scored label was missing in any of these runs, so operational failure equals the error count. Every label that did not receive an applied fused update still matched its local prediction: 0 violations across 306 runs.

## Figure 10: deadline, packet loss held at 0

Local detection finishes at 20 ms. The fused update arrives at 31.5 ms. On 1,200 queries and 3,600 labels:

| Deadline | Policy | Mean error | R2 | R3 | Late agent updates | Detector jobs | Edge jobs | Bytes | Energy (J/frame) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 21 ms | Local | 731/3,600 = 20.306% | 246/1,200 = 20.500% | 4/1,200 = 0.333% | 0 | 1,800 | 0 | 0 | 0.24000 |
| 21 ms | Conservative F0 | 731/3,600 = 20.306% | 246/1,200 = 20.500% | 4/1,200 = 0.333% | 2,850 | 1,800 | 600 | 3,907,584 | 0.25774 |
| 21 ms | Expert override | 731/3,600 = 20.306% | 246/1,200 = 20.500% | 4/1,200 = 0.333% | 3,600 | 1,800 | 600 | 3,916,800 | 0.25776 |
| 32 ms | Local | 731/3,600 = 20.306% | 246/1,200 = 20.500% | 4/1,200 = 0.333% | 0 | 1,800 | 0 | 0 | 0.24000 |
| 32 ms | Conservative F0 | 508/3,600 = 14.111% | 246/1,200 = 20.500% | 6/1,200 = 0.500% | 0 | 1,800 | 600 | 3,907,584 | 0.25774 |
| 32 ms | Expert override | 48/3,600 = 1.333% | 16/1,200 = 1.333% | 16/1,200 = 1.333% | 0 | 1,800 | 600 | 3,916,800 | 0.25776 |

The manuscript’s 20.31%, 14.11%, and 1.33% are these rates. At 21 ms, F0 has already accepted 950 of 1,200 queries and the override has accepted all 1,200, but none of those updates are applied. The scored labels remain the local labels. Jobs, bytes, and energy are the same numbers recorded at 32 ms, when the same updates arrive in time. Figure 10 is `fig6_deadline_cliff.pdf`.

Across all 12 deadlines and all six seeds, energy, detector jobs, edge jobs, and bytes do not change with the deadline. Through 31.5 ms, both fusion policies have the same mean error, R2, and R3 as local, and every accepted update is late. From 32 ms onward, every accepted update is applied. At 32 ms the six local mean errors lie in 20.028–20.667%. Conservative F0 lies in 13.694–14.250% with R2 unchanged. The override lies in 1.250–2.083%, and its R2 equals its mean error because it copies A.

## Figure 12: acceptance threshold, deadline not binding

This grid is the original nested draw with 1, 2, and 4 queries per frame. It is not the deadline draw above, so its 2-query local error is 20.583% rather than 20.306%. Detector jobs stay at 1,800 and edge jobs stay at 600 for every threshold, including the threshold that accepts nothing.

At two queries per frame and threshold 0.90, conservative F0 accepts 956/1,200 queries (79.67%) but sends a downlink on 574/600 frames (95.67%). At four queries per frame the same threshold accepts 79.38% of queries and sends a downlink on all 600 frames. With one query per frame, the query rate and the frame rate are the same 78.00%. One accepted query is enough to transmit the frame result.

Raising the threshold to 0.999 accepts 0 queries and sends 0 downlinks. Energy falls only from about 0.25774 J/frame to 0.25736 J/frame, 17.356 mJ above local. The remaining cost is the 1,800 detector runs, 600 edge decisions, and 3,686,400 upload bytes. The manuscript’s “about 0.25736 J/frame” is this rejected-everything case. Local energy on the same frames is 0.24000 J/frame, with 1,800 detector runs, 0 edge jobs, and 0 bytes. The expert override follows the same rejection at 0.999. At 0.90 on this 2-query draw it shares every query, mean error is 42/3,600 = 1.167%, and its energy is 0.25776 J/frame. Figure 12 is `fig5_sunk_cost_and_roi_reuse.pdf`.

## Packet loss, deadline held at 150 ms

The loss sweep reuses each seed’s deadline trace and changes only the loss probability. Local has no transfer, so its error and its 0.24000 J/frame do not move. Detector jobs remain 1,800 for every policy and every loss rate.

On seed `77109`:

| Loss | Policy | Mean error | R2 | R3 | Unapplied updates | Edge jobs | Bytes | Messages lost | Energy (J/frame) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0% | Conservative F0 | 14.111% | 20.500% | 0.500% | 0 | 600 | 3,907,584 | 0/3,528 | 0.25774 |
| 0% | Expert override | 1.333% | 1.333% | 1.333% | 0 | 600 | 3,916,800 | 0/3,600 | 0.25776 |
| 10% | Conservative F0 | 16.361% | 20.500% | 0.417% | 196 | 430 | 3,843,840 | 307/3,030 | 0.25508 |
| 10% | Expert override | 7.861% | 6.667% | 1.000% | 240 | 430 | 3,851,520 | 309/3,090 | 0.25509 |
| 25% | Conservative F0 | 18.417% | 20.500% | 0.333% | 310 | 259 | 3,782,400 | 639/2,550 | 0.25241 |
| 25% | Expert override | 14.056% | 12.583% | 0.583% | 380 | 259 | 3,785,856 | 642/2,577 | 0.25241 |
| 50% | Conservative F0 | 19.806% | 20.500% | 0.333% | 170 | 70 | 3,712,128 | 1,024/2,001 | 0.24945 |
| 50% | Expert override | 19.139% | 18.833% | 0.417% | 208 | 70 | 3,713,280 | 1,027/2,010 | 0.24945 |
| 100% | Conservative F0 | 20.306% | 20.500% | 0.333% | 0 | 0 | 3,686,400 | 1,800/1,800 | 0.24836 |
| 100% | Expert override | 20.306% | 20.500% | 0.333% | 0 | 0 | 3,686,400 | 1,800/1,800 | 0.24836 |

Conservative F0 keeps local’s R2 at every loss rate and every seed. At 100% loss both fusion policies return the local error, because every upload is lost and the edge decision never starts. The 1,800 upload attempts are still charged: 3,686,400 bytes and 0.24836 J/frame, against local’s 0.24000 J/frame and 0 bytes. Across the six seeds, 100% loss matches local error exactly, while 10% loss leaves conservative F0 mean error in 15.806–16.583% and the override in 7.750–8.833%.
