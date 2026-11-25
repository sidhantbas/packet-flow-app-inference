Flow-level paired check: old 20261001T173854Z_034_meta_gate,20261009T172902Z_062_production_s2027,20261009T173025Z_062_production_s2028,20261009T173146Z_062_production_s2029,20261009T173307Z_062_production_s2030 vs new 20261009T201045Z_077_FR,20261009T201104Z_077_FR_s2027,20261009T201124Z_077_FR_s2028,20261009T201143Z_077_FR_s2029,20261009T201202Z_077_FR_s2030

| app | flow | old right | new right | majority |
|---|---|---:|---:|---|
| facebook | flow_000024 | 0.96 | 0.96 | unchanged |
| facebook | flow_000231 | 0.00 | 0.00 | unchanged |
| facebook | flow_000368 | 0.48 | 0.48 | unchanged |
| facebook | flow_000610 | 0.92 | 0.94 | unchanged |
| facebook | flow_000617 | 0.88 | 0.88 | unchanged |
| facebook | flow_000799 | 0.84 | 0.84 | unchanged |
| facebook | flow_000809 | 0.86 | 0.86 | unchanged |
| facebook | flow_001145 | 0.32 | 0.32 | unchanged |
| facebook | flow_001168 | 0.86 | 0.86 | unchanged |
| facebook | flow_001324 | 0.72 | 0.72 | unchanged |
| facebook | flow_001331 | 0.78 | 0.78 | unchanged |
| instagram | flow_000003 | 0.08 | 0.08 | unchanged |
| instagram | flow_000210 | 0.88 | 0.88 | unchanged |
| instagram | flow_000215 | 0.88 | 0.88 | unchanged |
| instagram | flow_000216 | 0.00 | 0.00 | unchanged |
| instagram | flow_000359 | 0.82 | 0.82 | unchanged |
| instagram | flow_000360 | 1.00 | 1.00 | unchanged |
| instagram | flow_000379 | 0.00 | 0.00 | unchanged |
| instagram | flow_000477 | 0.98 | 0.98 | unchanged |
| instagram | flow_000604 | 0.98 | 0.98 | unchanged |
| instagram | flow_000609 | 1.00 | 1.00 | unchanged |
| instagram | flow_000813 | 1.00 | 1.00 | unchanged |
| instagram | flow_000837 | 1.00 | 1.00 | unchanged |
| instagram | flow_000838 | 1.00 | 1.00 | unchanged |
| instagram | flow_001185 | 0.00 | 0.00 | unchanged |
| instagram | flow_001321 | 1.00 | 1.00 | unchanged |
| instagram | flow_001323 | 1.00 | 1.00 | unchanged |
| instagram | flow_001325 | 1.00 | 1.00 | unchanged |
| instagram | flow_001327 | 1.00 | 1.00 | unchanged |
| instagram | flow_001328 | 1.00 | 1.00 | unchanged |

McNemar (facebook/instagram flows, majority correctness): fixed 0, broken 0, exact p = 1.000
facebook F1 difference (new - old): +0.002, 95% bootstrap interval [-0.001, +0.008] -> unproven (interval crosses zero)
instagram F1 difference (new - old): +0.001, 95% bootstrap interval [-0.001, +0.003] -> unproven (interval crosses zero)
