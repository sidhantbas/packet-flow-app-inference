Flow-level paired check: old 20261009T182114Z_067_TH,20261009T182221Z_067_TH_s2027,20261009T182327Z_067_TH_s2028 vs new 20261009T182508Z_067_THTW,20261009T182615Z_067_THTW_s2027,20261009T182721Z_067_THTW_s2028

| app | flow | old right | new right | majority |
|---|---|---:|---:|---|
| facebook | flow_000024 | 0.97 | 0.97 | unchanged |
| facebook | flow_000231 | 0.00 | 0.00 | unchanged |
| facebook | flow_000368 | 0.57 | 0.57 | unchanged |
| facebook | flow_000610 | 0.93 | 0.93 | unchanged |
| facebook | flow_000617 | 0.90 | 0.90 | unchanged |
| facebook | flow_000799 | 0.83 | 0.83 | unchanged |
| facebook | flow_000809 | 0.80 | 0.80 | unchanged |
| facebook | flow_001145 | 0.37 | 0.37 | unchanged |
| facebook | flow_001168 | 0.80 | 0.80 | unchanged |
| facebook | flow_001324 | 0.63 | 0.63 | unchanged |
| facebook | flow_001331 | 0.80 | 0.80 | unchanged |
| instagram | flow_000003 | 0.10 | 0.10 | unchanged |
| instagram | flow_000210 | 0.83 | 0.83 | unchanged |
| instagram | flow_000215 | 0.83 | 0.83 | unchanged |
| instagram | flow_000216 | 0.00 | 0.00 | unchanged |
| instagram | flow_000359 | 0.63 | 0.63 | unchanged |
| instagram | flow_000360 | 0.97 | 0.97 | unchanged |
| instagram | flow_000379 | 0.00 | 0.00 | unchanged |
| instagram | flow_000477 | 0.80 | 0.80 | unchanged |
| instagram | flow_000604 | 0.97 | 0.97 | unchanged |
| instagram | flow_000609 | 1.00 | 1.00 | unchanged |
| instagram | flow_000813 | 1.00 | 1.00 | unchanged |
| instagram | flow_000837 | 1.00 | 1.00 | unchanged |
| instagram | flow_000838 | 1.00 | 1.00 | unchanged |
| instagram | flow_001185 | 0.00 | 0.00 | unchanged |
| instagram | flow_001321 | 0.97 | 0.97 | unchanged |
| instagram | flow_001323 | 1.00 | 1.00 | unchanged |
| instagram | flow_001325 | 1.00 | 1.00 | unchanged |
| instagram | flow_001327 | 1.00 | 1.00 | unchanged |
| instagram | flow_001328 | 1.00 | 1.00 | unchanged |

McNemar (facebook/instagram flows, majority correctness): fixed 0, broken 0, exact p = 1.000
facebook F1 difference (new - old): -0.016, 95% bootstrap interval [-0.056, +0.000] -> unproven (interval crosses zero)
instagram F1 difference (new - old): +0.012, 95% bootstrap interval [+0.000, +0.040] -> unproven (interval crosses zero)
