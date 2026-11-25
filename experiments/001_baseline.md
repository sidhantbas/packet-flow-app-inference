---
title: 001 — Baseline reproduction
created: 2026-09-29
creator: sidhantbas
experiment:
  id: '001'
  tasks:
  - task1
  - task2
  lever: evaluation
  status: measured
  verdict: 'RandomForest baseline on the single validation split: Task 1 0.713, Task 2 0.743 (72.8 points); superseded by repeated CV in 002'
---
# 001 — Baseline reproduction

- **Date:** 2026-09-29
- **Script:** `src/baseline.py`
- **Data:** `data/official/dataset/` (train → validation; each task uses only its own folder)
- **Features:** all columns except `flow_id`, `split`, `server_port`, `start_rel`; `transport` encoded as udp=1, tcp=0 (17 features)
- **Model:** `RandomForestClassifier(n_estimators=500, class_weight="balanced")`, seeds 0–4, scores averaged
- **Evaluation:** single validation split (83 flows). No cross-validation yet; see next steps.

## Results — validation macro F1 (mean ± std over 5 seeds)

| Task | Macro F1 | Score (×50) |
|---|---|---|
| task1_static | 0.7131 ± 0.0111 | 35.66 |
| task2_realtime_prefix5 | 0.7429 ± 0.0093 | 37.14 |
| **Total** | | **72.80** |

### Per-class F1 (mean over 5 seeds)

| Class (val n) | task1_static | task2_prefix5 |
|---|---|---|
| facebook (3) | 0.000 | 0.400 |
| google (33) | 0.873 | 0.873 |
| instagram (5) | 0.911 | 0.889 |
| mozilla (10) | 0.863 | 0.828 |
| x (18) | 0.862 | 0.773 |
| youtube (14) | 0.770 | 0.694 |

## Differences from the expected numbers (~0.75 / ~0.73, Facebook ≈ 0)

- Task 1 comes out at **0.713, not ~0.75**. The same model with `start_rel` kept gives **0.751** on task 1 and 0.764 on task 2. The expected task 1 figure was probably produced with `start_rel` included. This supports the leakage concern, since `start_rel` alone adds about 4 points on task 1.
- Task 2 comes out slightly *higher* than expected (0.743 vs ~0.73). In task 2, the model finds 1 of the 3 validation Facebook flows in every seed (F1 = 0.40). In task 1, Facebook is exactly 0.
- Variant checks (5-seed mean macro F1, task1 / task2):
  - drop server_port + start_rel (spec): 0.7131 / 0.7429
  - keep start_rel: 0.7512 / 0.7635
  - keep server_port: 0.7205 / 0.7479
  - keep both: 0.7446 / 0.7625
- With 3 validation Facebook flows, one flow flips that class's F1 by about 0.4 and macro F1 by about 0.07. The single validation split is very noisy.

## Next steps
- Move to repeated stratified CV on train+validation (330 flows) as the standard evaluation.
- Target Facebook directly, because it is worth about 1/6 of each task's macro F1.
