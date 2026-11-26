# CooperScene three-vehicle evaluation

The frozen protocol was not changed. Octopus-main was not edited.
Reliability rates are the validation region-error rates stored in the manifest.
They are not object-level F1, and they were not refit on the test split.
The predeclared expert is vehicle 3, the lowest validation rate.
Ties would break toward the smaller vehicle id. Test performance was not used.

Distinct result IDs were checked as three different strings.
That check does not establish statistically independent errors.
The pairwise correlations below are the local detectors' error indicators.

## Verification

The existing `convert_to_trace` accepted the export: three vehicles, synchronized region identities, one shared truth file, and matching per-vehicle files.
The existing `perform_evaluation` then ran local, majority, and the F0 threshold list.

## Policies

| Policy | Mean error | R2 | R3 | Joint false alarms | Joint misses | Corrections | Introduced errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| local | 0.0928 | 0.0300 | 0.0000 | 0 | 0 | 0 | 0 |
| majority | 0.0300 | 0.0300 | 0.0300 | 1 | 35 | 262 | 36 |
| weighted | 0.0300 | 0.0300 | 0.0300 | 1 | 35 | 262 | 36 |
| conservative_f0 | 0.0603 | 0.0300 | 0.0267 | 0 | 32 | 149 | 32 |
| expert_override | 0.0603 | 0.0300 | 0.0267 | 0 | 32 | 149 | 32 |
| always_a | 0.0867 | 0.0867 | 0.0867 | 3 | 101 | 197 | 175 |

## Frame bootstrap versus local

Seed 77232, 2000 draws, resampling the 30 physical frames.
The interval is the 2.5 and 97.5 percentiles of the paired difference.

| Policy minus local | Mean error | R2 | R3 |
|---|---|---|---|
| majority | [-0.0675, -0.0578] | [+0.0000, +0.0000] | [+0.0217, +0.0392] |
| weighted | [-0.0675, -0.0578] | [+0.0000, +0.0000] | [+0.0217, +0.0392] |
| conservative_f0 | [-0.0350, -0.0297] | [+0.0000, +0.0000] | [+0.0192, +0.0342] |
| expert_override | [-0.0350, -0.0297] | [+0.0000, +0.0000] | [+0.0192, +0.0342] |
| always_a | [-0.0114, -0.0003] | [+0.0508, +0.0625] | [+0.0792, +0.0950] |

## Local error correlation

- Vehicles 1 and 2: -0.0695
- Vehicles 1 and 3: -0.1089
- Vehicles 2 and 3: 0.3061

## One shared lineage

Repeating conservative F0 with all three vehicles in one dependence group removes the assumption that distinct result IDs are independent evidence.

- conservative_f0_shared_lineage: mean error 0.0928, R2 0.0300, R3 0.0000, accepted fraction 0.0000
- expert_override_shared_lineage: mean error 0.0928, R2 0.0300, R3 0.0000, accepted fraction 0.0000

## Existing study script

- local_only: mean error 0.0928, R2 0.0300, R3 0.0000
- majority: mean error 0.0300, R2 0.0300, R3 0.0300
- f0_0.750: mean error 0.0300, R2 0.0300, R3 0.0300
- f0_0.850: mean error 0.0489, R2 0.0300, R3 0.0275
- f0_0.900: mean error 0.0603, R2 0.0300, R3 0.0267
- f0_0.950: mean error 0.0928, R2 0.0300, R3 0.0000
- f0_0.990: mean error 0.0928, R2 0.0300, R3 0.0000

## Against the P1 synthetic three-agent result

P1 Table 3, shock 0.18, seed 77109, 4,000 queries:
local mean error 0.2003, R2 0.1980, R3 0.0020;
majority 0.1980, 0.1980, 0.1980;
conservative F0 0.1366, 0.1980, 0.0040;
expert override 0.0138, 0.0138, 0.0138, and on that draw it copied A on every query.
F0 there lowered mean error and left R2 unchanged, while majority turned R2 into R3.
The expert result depended on a declared error of 1.5 percent. The override rule does not fire above 5 percent.
Compare the table above with those signs rather than with the synthetic percentages.

Validation rates used here: vehicle 1 0.168099, vehicle 2 0.136581, vehicle 3 0.112703.
Vehicle 3's validation rate is above 0.05, so the P1 expert override does not engage. It is reported anyway, and it should match conservative F0. Always-A still copies that vehicle on every region.
Energy and latency from the stock script remain the hypothetical E1 profile.
