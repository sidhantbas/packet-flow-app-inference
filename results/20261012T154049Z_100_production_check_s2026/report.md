# Run 20261012T154049Z_100_production_check_s2026

- **Experiment:** 100 (production_check_s2026)
- **Question:** Task 1: new production (100 FB, task1_cross_task) on cv_seed 2026, the champion reference for later experiments
- **When:** 2026-10-12T15:40:26+00:00 → 2026-10-12T15:40:49+00:00 (23.7 s)
- **Device:** Sids-MacBook-Pro-2 · Apple M4 Pro · 14 cores · 48.0 GB · Python 3.13.1
- **Git:** `30f0adb` (dirty)
- **Config:** `{"model": "task1_cross_task", "cv_seed": 2026, "features": "task1_with_prefix_features", "features_fn": "task1_with_prefix_features"}`

## Scores (repeated stratified CV)

| Task | Macro F1 | Fold std | facebook | google | instagram | mozilla | x | youtube |
|---|---|---|---|---|---|---|---|---|
| task1_static | **0.8573** | 0.0689 | 0.719 | 0.915 | 0.775 | 0.946 | 0.957 | 0.832 |

## Checks

- **warn** `dirty-tree`: Uncommitted changes in 6 file(s); the commit alone does not reproduce this run (code hashes are recorded).
- **info** `cross-task-input`: task1_static also reads ['task2_realtime_prefix5/train_features.csv', 'task2_realtime_prefix5/validation_features.csv', 'task2_realtime_prefix5/test_features.csv']; allowed (condition 2 restricts Task 2 only) but must be disclosed in the report.
