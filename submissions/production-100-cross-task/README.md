---
title: "Production submission (2026-10-12): Task 1 100 FB + Task 2 014"
created: 2026-10-12
creator: sidhantbas
description: Submission file of the production models after experiment 100 was adopted (user decision 2026-10-12), with hashes, validation results, the one prediction that differs from the ranked entry, and the upload conditions.
relation:
  - ../../experiments/100_cross_task_meta_rescue.md
  - ../../reports/closing-the-f1-gap-2026-10-12.md
  - ../README.md
---

# Production submission: 100 FB + 014

**Status: production file since 2026-10-12; uploaded 2026-10-12 (upload 8): Task 1 0.822, Task 2 0.905, total 86.36; the ranked
entry by the rule fixed before the score. The score is information only.** Task 1 is the 089 bundle plus the cross-task Meta rescue of
experiment 100 (arm FB), adopted as a deliberate exception by the user. Task 2 is unchanged (014).

## Difference from the ranked entry

Compared with [`production-089-bundle/`](../production-089-bundle/) (upload 7, 87.24), one Task 1 prediction changes and Task 2
is identical.

| Flow | Ranked entry | This file | Why |
|---|---|---|---|
| `flow_000223` | youtube | facebook | The Task 2 model calls its opening instagram while the 089 bundle calls it non-Meta (in CV, 137 of 138 such flows were not what Task 1 said) |

## Files

| File | Content | SHA-256 |
|---|---|---|
| `submission.zip` | `task1_static.csv`, `task2_realtime_prefix5.csv` (the upload file) | `02ea4690bb6ca7362845491fcfa2c9c1a7560656dbabcbfee08d57d8101253d7` |
| `submission.json` | Both tasks, 81 flows each; identical to `../submission.json` | `8069ed258c3477f9604d2ec7b091f13a475dcc78de9768dc72b9ed9403bad62c` |
| [`config.json`](config.json) | Models, features, inputs, exclusions, command | — |
| [`manifest.json`](manifest.json) | Git commit, code and data SHA-256 | — |
| [`validation.json`](validation.json) | All checks below | — |
| [`comparison.json`](comparison.json) | Differences from the ranked entry and from the 88.11 file | — |

Zip timestamps differ between builds; the JSON is the reproducible artifact.

**Reproduce:** `.venv/bin/python src/make_final_candidate.py --out submissions/production-100-cross-task` (builds twice and checks
the JSON is byte-identical). `.venv/bin/python src/make_submission.py` writes the same predictions to `submissions/submission.*`.

## Models (selected by cross-validation only)

| Task | Model | Inputs | Local evidence |
|---|---|---|---|
| Task 1 | `models.task1_cross_task` (100 FB): `models.task1_bundle` (089) plus an inner copy of `models.task2_model` (014) fitted on the same rows; a flow the inner model calls instagram while the bundle calls it non-Meta becomes facebook | 34 columns: 17 Task 1 + 17 disclosed Task 2 statistics of the same flow | CV macro F1 0.857 (seed 2026; 089: 0.849); Δ > 0 on all 10 fresh fold sets (ordinary mean +0.011, BETTER 1 of 5; twin-aware +0.030, BETTER 5 of 5) |
| Task 2 | `models.task2_model` (014) | 12 no-timing columns, `task2_realtime_prefix5/` only | CV macro F1 0.754 (seed 2026) |

Task 1 champion run `20261012T154049Z_100_production_check_s2026`. The registry model reproduces the experiment's FB runs exactly
(seeds 2026 and 2046).

## Validation (`validation.json`)

| Check | Result |
|---|---|
| Rebuild produces a byte-identical JSON | ✅ |
| 81 unique test IDs per task, equal to the test features and the sample submission | ✅ |
| Labels among the six apps | ✅ |
| No `flow_id`, `split`, `start_rel` or `server_port` among the features | ✅ |
| Task 2 reads only `task2_realtime_prefix5/` files | ✅ |
| Official loader accepts `submission.json` and `submission.zip` | ✅ |
| No `metadata.json` or `label_counts` in the pipeline code | ✅ |

## Upload conditions

- **Uploads:** the platform accepted this eighth upload, so our earlier count of 7 was not the limit; the allowance is still
  unverified.
- **Ranked entry:** this is the production file, adopted on cross-validation before any score. If it is uploaded, it becomes
  the ranked entry whatever it scores, by the rule in [`../README.md`](../README.md).
- **Score is information only:** this file differs from the ranked entry in one flow, so its score reveals that flow's label.
  It is never used to choose files, models or further changes (challenge condition 1; experiment 080).
- **Disclosure:** Task 1 now contains a model trained on Task 2 files. Allowed (condition 2 restricts only Task 1 data in Task 2)
  and disclosed in the technical report, like 022.
