---
title: '005: First complete submission'
created: 2026-09-29
creator: sidhantbas
experiment:
  id: '005'
  tasks:
  - task1
  - task2
  lever: submission
  status: submission
  verdict: 'First complete submission pipeline (SoftVote, both tasks): official-scorer check, seed stability, compute cost'
---
# 005: First complete submission

- **Date:** 2026-09-29
- **Scripts:**
  - `src/models.py`: shared model definitions; `SoftVote` moved here from the 004 script, which now imports it
  - `src/make_submission.py`: final training and submission files
  - `src/exp005_checks.py`: official-scorer check, seed stability, compute cost. Raw output is in `experiments/005_checks_output.txt`.
- **Model (both tasks):** `SoftVote(seed=0)`, the unweighted mean `predict_proba` of RF (500 trees, balanced), ExtraTrees (500 trees, balanced) and LightGBM (300 trees, lr 0.05, 15 leaves, min_child_samples 5, balanced). The model choice is recorded in CLAUDE.md under "Current submission model".
- **Features:** the 17 default columns (no `start_rel`, no `server_port`, transport as udp=1).
- **Training data:** train+validation (330 flows) per task, each task read only from its own folder.

## 1. Ceilings (from 004 Part A, not recomputed)

| Task | Ceiling, all 17 columns | Ceiling, 12 size/count columns (no timing) | Facebook F1 ceiling | Instagram F1 ceiling |
|---|---|---|---|---|
| task1_static | 1.000 (no identical vectors) | 1.000 (no mixed groups) | 1.000 | 1.000 |
| task2_realtime_prefix5 | 1.000 (no identical vectors) | **0.930** (7 mixed groups, 80 flows) | 0.857 | 0.900 (0.905 if optimised for Instagram alone) |

## 2. Pipeline check with the official scorer

The ensemble was trained on **train only** and predicted **validation** for both tasks. A temporary annotation file `{"tasks": {task: {flow_id: label}}}` was built from the validation labels in a temp directory and deleted afterwards. The submission was scored with the unmodified `evaluate()` from `data/official/evaluation_script/main.py`, phase `dev`.

| | Task 1 | Task 2 |
|---|---|---|
| Macro F1 | **0.7447** | **0.7381** |
| Accuracy | 0.8795 | 0.7831 |
| Score | 37.23 | 36.90 |
| **Total** | | **74.14** |

- The JSON and ZIP submission formats gave identical results.
- **No format errors, missing IDs or invalid labels.** `evaluate()` raises an error on any of these, and it raised none.
- The written **test** files (`submissions/submission.json`, `submissions/submission.zip`) were parsed with the official `_load_submission`. Each task has 81/81 test IDs, matching `test_features.csv` and `sample_submission.csv` exactly, and all labels are in the allowed set.
- For reference, the RF baseline on the same split (001) scored 0.713 / 0.743. This is one 83-flow split, so it does not measure the ensemble's real gain; the CV figures in 004 do.

## 3. Stability over 10 seeds (final model on train+validation, seeds 0–9, test predictions)

| Task | Test flows whose label changes across seeds |
|---|---|
| task1_static | **1 / 81** (flow_000095: google 8×, youtube 2×) |
| task2_realtime_prefix5 | **0 / 81** |

Predicted test label distribution (seed 0 = the submitted model) next to the published test counts from metadata.json:

| Class | T1 predicted | T1 min–max over seeds | T1 unstable | T2 predicted | T2 min–max | T2 unstable | Expected (metadata) |
|---|---|---|---|---|---|---|---|
| facebook | 1 | 1–1 | 0 | 2 | 2–2 | 0 | 2 |
| google | 40 | 39–40 | 1 | 33 | 33–33 | 0 | 33 |
| instagram | 2 | 2–2 | 0 | 5 | 5–5 | 0 | 4 |
| mozilla | 7 | 7–7 | 0 | 7 | 7–7 | 0 | 10 |
| x | 22 | 22–22 | 0 | 24 | 24–24 | 0 | 19 |
| youtube | 9 | 9–10 | 0 | 10 | 10–10 | 0 | 13 |

- The submission does not depend on the random seed.
- *(Removed 2026-09-30.)* This bullet compared predicted test class counts with the aggregate test `label_counts` in `metadata.json`. Those counts are derived from test labels, so under challenge condition 1 we no longer look at them, even for sanity checks. They were never used for training or model selection, and nothing was adjusted. The column was also removed from `src/exp005_checks.py` and `005_checks_output.txt`.

## 4. Compute cost (for the technical report)

Machine: Apple M4 Pro (14 cores, 48 GB RAM), Python 3.13.1, scikit-learn 1.9.1, LightGBM 4.7.0. All three models use all cores (`n_jobs=-1`). Times are the median of 3 runs.

| Task | Training (330 flows × 17 features) | Inference (81 flows, batch) | Per flow | Model size (pickle) |
|---|---|---|---|---|
| task1_static | 3.4 s | 54 ms | 0.67 ms | 24.4 MB (RF 6.2, ExtraTrees 16.0, LightGBM 2.2) |
| task2_realtime_prefix5 | 4.0 s | 55 ms | 0.67 ms | 25.9 MB (RF 7.0, ExtraTrees 16.3, LightGBM 2.6) |

Most of the size is ExtraTrees (fully grown random trees). If size matters for the report, fewer trees or a depth limit would shrink it; that has not been tested.

## 5. Output

- `submissions/submission.json` (official JSON format) and `submissions/submission.zip` (`task1_static.csv`, `task2_realtime_prefix5.csv`).
- **Expected score from CV (004):** task 1 ≈ 0.771, task 2 ≈ 0.686, total ≈ **72.8** (fold std ±0.07 per task, mostly from how the 2 test Facebook flows land).
- `reports/findings_summary.md`: plain-English summary of 001–005 for Charles.
