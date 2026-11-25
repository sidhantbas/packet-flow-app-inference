Flow-level paired check: old 20261001T173854Z_034_meta_gate,20261009T172902Z_062_production_s2027,20261009T173025Z_062_production_s2028 vs new 20261009T182114Z_067_TH,20261009T182221Z_067_TH_s2027,20261009T182327Z_067_TH_s2028

| app | flow | old right | new right | majority |
|---|---|---:|---:|---|
| facebook | flow_000024 | 0.93 | 0.97 | unchanged |
| facebook | flow_000231 | 0.00 | 0.00 | unchanged |
| facebook | flow_000368 | 0.47 | 0.57 | fixed |
| facebook | flow_000610 | 0.93 | 0.93 | unchanged |
| facebook | flow_000617 | 0.90 | 0.90 | unchanged |
| facebook | flow_000799 | 0.87 | 0.83 | unchanged |
| facebook | flow_000809 | 0.80 | 0.80 | unchanged |
| facebook | flow_001145 | 0.33 | 0.37 | unchanged |
| facebook | flow_001168 | 0.80 | 0.80 | unchanged |
| facebook | flow_001324 | 0.63 | 0.63 | unchanged |
| facebook | flow_001331 | 0.77 | 0.80 | unchanged |
| instagram | flow_000003 | 0.10 | 0.10 | unchanged |
| instagram | flow_000210 | 0.83 | 0.83 | unchanged |
| instagram | flow_000215 | 0.83 | 0.83 | unchanged |
| instagram | flow_000216 | 0.00 | 0.00 | unchanged |
| instagram | flow_000359 | 0.83 | 0.63 | unchanged |
| instagram | flow_000360 | 1.00 | 0.97 | unchanged |
| instagram | flow_000379 | 0.00 | 0.00 | unchanged |
| instagram | flow_000477 | 1.00 | 0.80 | unchanged |
| instagram | flow_000604 | 0.97 | 0.97 | unchanged |
| instagram | flow_000609 | 1.00 | 1.00 | unchanged |
| instagram | flow_000813 | 1.00 | 1.00 | unchanged |
| instagram | flow_000837 | 1.00 | 1.00 | unchanged |
| instagram | flow_000838 | 1.00 | 1.00 | unchanged |
| instagram | flow_001185 | 0.00 | 0.00 | unchanged |
| instagram | flow_001321 | 1.00 | 0.97 | unchanged |
| instagram | flow_001323 | 1.00 | 1.00 | unchanged |
| instagram | flow_001325 | 1.00 | 1.00 | unchanged |
| instagram | flow_001327 | 1.00 | 1.00 | unchanged |
| instagram | flow_001328 | 1.00 | 1.00 | unchanged |

McNemar (facebook/instagram flows, majority correctness): fixed 1, broken 0, exact p = 1.000
facebook F1 difference (new - old): -0.009, 95% bootstrap interval [-0.037, +0.012] -> unproven (interval crosses zero)
instagram F1 difference (new - old): -0.008, 95% bootstrap interval [-0.030, +0.008] -> unproven (interval crosses zero)
