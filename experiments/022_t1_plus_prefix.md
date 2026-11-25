---
title: '022: Task 1 with first-5-packet statistics'
created: 2026-09-30
creator: sidhantbas
description: Does Task 1 improve when it also sees the Task 2 (first-5-packet) statistics of the same flow?
experiment:
  id: '022'
  tasks:
  - task1
  lever: features
  status: adopted
  verdict: 'Task 1 + the 17 first-5-packet statistics (KeepClassBlend, facebook calls of the 17-column model kept): 0.807 (+0.036), rule v2 on 5 seeds'
  production: Task 1 whole-flow expert with the first-5-packet columns
---
# 022: Task 1 with first-5-packet statistics

- **Date:** 2026-09-30
- **Question:** Does Task 1 improve when it also sees the Task 2 (first-5-packet) statistics of the same flow?
- **Status:** done; **adopted for Task 1** (user decision, 2026-09-30)
- **Script:** `src/exp022_t1_plus_prefix.py` (`models.ColumnBlend`, `models.KeepClassBlend`)
- **Runs:** `results/*_022_*`
- **Reference:** task 1 champion (`006_softvote`, 0.7705)

## Context

The one Final Test Phase submission (2026-09-30, file of commit 6b76821) scored Task 1 0.766, Task 2 0.905,
total 83.56. The Task 1 test score matches CV (0.771), and Task 1 is where the leaderboard gap is. This number is
recorded for information only; it chose the direction of this experiment but **no model choice is made from it**.

Condition 2 forbids Task 1 (full-flow) features in Task 2 predictions. It does not forbid the reverse. Both tasks
share flow_ids, so Task 1 can add the Task 2 file's columns for the same flow (prefixed `p5_`, joined on flow_id).
Any adoption must be disclosed in the report.

## Results (Task 1, vs champion, cv_seed 2026)

| Variant | Macro F1 | Δ | W / L | facebook Δ |
|---|---|---|---|---|
| plus_p5_all: 17 + 17 prefix columns | 0.781 | +0.011 | 31 / 19, near miss | −0.082 |
| plus_p5_notime: 17 + 12 prefix columns | 0.775 | +0.004 | 31 / 19, near miss | −0.123 |
| blend_t1_p5all: mean proba of champion and plus_p5_all | — | +0.019 | 35 / 15, BETTER | −0.082 |
| **blend_keep_fb: blend, but flows the champion calls facebook stay facebook** | **0.807** | **+0.036** | **43 / 7, BETTER** | +0.008 |

The prefix columns help the four large classes (google, x, youtube, mozilla +0.03 to +0.05 on every variant) and
dilute Facebook, whose Task 1 signal is full-flow timing (010). The blend alone failed confirmation (2027: +0.006,
30/19; 2028: +0.019, 34/16), with Facebook −0.05 to −0.10 each time, which motivated `blend_keep_fb`.

blend_keep_fb per class (seed 2026): facebook +0.008, google +0.033, instagram +0.035, mozilla +0.036, x +0.048,
youtube +0.055.

## Confirmation of blend_keep_fb

| cv_seed | Champion | blend_keep_fb | Δ | W / L / T | facebook Δ | Note |
|---|---|---|---|---|---|---|
| 2026 | 0.771 | 0.807 | +0.036 | 43 / 7 / 0 | +0.008 | |
| 2027 | 0.785 | 0.806 | +0.021 | 35 / 14 / 1 | −0.027 | seen by the plain blend |
| 2028 | 0.761 | 0.791 | +0.030 | 37 / 13 / 0 | −0.003 | seen by the plain blend |
| 2029 | 0.783 | 0.811 | +0.028 | 37 / 13 / 0 | −0.003 | untouched |
| 2030 | 0.777 | 0.815 | +0.039 | 45 / 5 / 0 | +0.023 | untouched |

The variant was designed after seeing seeds 2026–2028, so two untouched seeds (2029, 2030) were added. It passes
rule v2 on all five.

## Caveats

- Rules: this uses Task 2 files to predict Task 1. Condition 2's wording only forbids the other direction, but it
  should be confirmed with Charles (and, if unsure, the organisers) and disclosed in the report.
- Facebook is kept, not improved: the gain comes from the four large classes.

## Decision

**Adopted for Task 1** after the user reviewed the five conditions (condition 2 restricts Task 1 → Task 2 only).
- `cv.TASK_FEATURES["task1_static"] = task1_with_prefix_features` (17 Task 1 + 17 prefix columns, joined on flow_id;
  the Task 2 files it reads are hashed into each run's manifest and flagged `cross-task-input` for disclosure).
- `models.task1_model = KeepClassBlend((T1_COLS, "all"), keep="facebook")`.
- `022_production_check` reproduces `022_blend_keep_fb` on all 50 folds; Task 2 unchanged. Champion task 1:
  `20260930T215907Z_022_blend_keep_fb` (0.8065).
- Rebuilt submission: 4 Task 1 test predictions change vs the submitted file (flow_000095 google → youtube,
  flow_000304 x → google, flow_000678 x → mozilla, flow_000885 google → youtube); Task 2 unchanged.
- Official-scorer pipeline check (train only → validation): Task 1 0.762 (was 0.745), Task 2 0.778, total 77.0.
- Disclosed in the technical report (Method, Compliance).
