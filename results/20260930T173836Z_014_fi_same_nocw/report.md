# Run 20260930T173836Z_014_fi_same_nocw

- **Experiment:** 014 (fi_same_nocw)
- **Question:** Does a facebook/instagram specialist (fi_same_nocw) beat the champion (cv_seed 2026)?
- **When:** 2026-09-30T17:38:27+00:00 → 2026-09-30T17:38:36+00:00 (8.6 s)
- **Device:** Sids-MacBook-Pro-2 · Apple M4 Pro · 14 cores · 48.0 GB · Python 3.13.1
- **Git:** `e7723e7` (dirty)
- **Config:** `{"model": "PairSpecialist:fi_same_nocw", "features": {"task1_static": "basic_features", "task2_realtime_prefix5": "no_timing_features"}, "cv_seed": 2026, "features_fn": null}`

## Scores (repeated stratified CV)

| Task | Macro F1 | Fold std | facebook | google | instagram | mozilla | x | youtube |
|---|---|---|---|---|---|---|---|---|
| task1_static | **0.7634** | 0.0807 | 0.537 | 0.831 | 0.739 | 0.857 | 0.884 | 0.731 |
| task2_realtime_prefix5 | **0.7544** | 0.0669 | 0.410 | 0.887 | 0.704 | 0.848 | 0.904 | 0.774 |

## task1_static vs `20260930T161714Z_006_softvote`

**INCONCLUSIVE**: Δ -0.0071 (paired std 0.0531), wins 5/50 (need 35), losses 10, ties 35. Δ is -0.10× the reference fold std.

| Class | Δ F1 | Wins | Losses |
|---|---|---|---|
| facebook | -0.047 | 4 | 10 |
| google | +0.000 | 0 | 0 |
| instagram | +0.004 | 6 | 8 |
| mozilla | +0.000 | 0 | 0 |
| x | +0.000 | 0 | 0 |
| youtube | +0.000 | 0 | 0 |

Flows (majority vote over repeats): fixed 1, broken 0.
- fixed `flow_000368` (facebook, was instagram)
- Fewer instagram → facebook: 14 → 11
- Fewer google → instagram: 22 → 21
- Fewer x → instagram: 5 → 4
- Fewer youtube → facebook: 2 → 1
- More facebook → instagram: 12 → 17
- More youtube → instagram: 11 → 12
- More x → facebook: 0 → 1
- More google → facebook: 4 → 5

## task2_realtime_prefix5 vs `20260930T170446Z_007_t2_drop_timing5`

**INCONCLUSIVE**: Δ +0.0182 (paired std 0.0263), wins 18/50 (need 35), losses 1, ties 31. Δ is 0.28× the reference fold std.

| Class | Δ F1 | Wins | Losses |
|---|---|---|---|
| facebook | +0.026 | 11 | 1 |
| google | +0.000 | 0 | 0 |
| instagram | +0.083 | 19 | 0 |
| mozilla | +0.000 | 0 | 0 |
| x | +0.000 | 0 | 0 |
| youtube | +0.000 | 0 | 0 |

Flows (majority vote over repeats): fixed 3, broken 0.
- fixed `flow_000379` (instagram, was facebook)
- fixed `flow_000604` (instagram, was facebook)
- fixed `flow_001323` (instagram, was facebook)
- Fewer instagram → facebook: 46 → 27
- Fewer google → instagram: 5 → 0
- More google → facebook: 5 → 10

## Checks

- **warn** `dirty-tree`: Uncommitted changes in 4 file(s); the commit alone does not reproduce this run (code hashes are recorded).
- **info** `zero-f1-folds`: task1_static: facebook has F1 = 0 in 10/50 folds.
- **info** `noise-driver`: task1_static: facebook fold std 0.32 drives most of the macro F1 noise.
- **info** `zero-f1-folds`: task2_realtime_prefix5: facebook has F1 = 0 in 15/50 folds.
- **info** `noise-driver`: task2_realtime_prefix5: facebook fold std 0.30 drives most of the macro F1 noise.
- **todo** `missing-log`: No experiments/014_*.md yet; write it (see experiments/TEMPLATE.md).
