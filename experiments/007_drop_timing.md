---
title: '007: Faster CV, and removing timing features'
created: 2026-09-30
creator: sidhantbas
description: (0) Does fold-parallel CV reproduce the champion exactly? (A–C) Does removing timing columns help?
experiment:
  id: '007'
  tasks:
  - task2
  lever: features
  status: adopted
  verdict: 'Task 2 without the 5 timing columns: +0.051 (40/50, every class up), confirmed on seeds 2027/2028; dropping min_iat in Task 1 has no effect'
  production: 'Task 2 features: 12 no-timing columns (cv.no_timing_features)'
---
# 007: Faster CV, and removing timing features

- **Date:** 2026-09-30
- **Question:** (0) Does fold-parallel CV reproduce the champion exactly? (A–C) Does removing timing columns help?
- **Status:** done
- **Script:** `src/exp007_drop_timing.py` (main runs), `src/exp007_drop_timing.py confirm` (confirmation)
- **Runs:** `results/*_007_*` (16 runs; `src/runs.py list 20`)
- **Reference:** `20260930T161714Z_006_softvote` (champion for both tasks at the start)

## Hypothesis

In Charles's permutation run (`data/charles/automl/results/feature-diagnostics-20260929T222807Z/`,
task 2 `permutation-summary.csv`), shuffling `duration`, `mean_iat`, `std_iat` or `max_iat` each made his
task 2 model slightly *better* (−0.006 to −0.011), and the timing group together only mattered 0.020.
Over the first 5 packets, timing likely reflects network jitter and handshake round trips rather than the
app, so trees overfit it. Task 1 `min_iat` is 0 in 98% of flows and had zero importance.

## Step 0: faster CV

One SoftVote fold on the M4 Pro: 0.53 s with single-threaded models, 0.91 s (2 threads), 1.08 s (4),
1.80 s (8), 3.31 s (`n_jobs=-1`). Now `models.MODEL_JOBS = 1` and `cv.evaluate()` runs the 50 folds
in parallel processes (`FOLD_JOBS = -1`; both overridable with `MISSION_P_MODEL_JOBS` / `MISSION_P_FOLD_JOBS`).

Result: the champion re-run (`007_softvote_fastcv`) ties the 006 run on all 50 folds in both tasks, with no
flow changing. A SoftVote run over both tasks now takes ~4 s instead of ~3 min.

## Results (SoftVote, cv_seed 2026, vs champion)

| Variant | Task | Macro F1 | Δ | Wins | Verdict |
|---|---|---|---|---|---|
| A: drop duration, mean/std/max IAT | task 2 | 0.7213 | +0.036 | 40/50 | BETTER |
| **B: drop all five timing columns** | task 2 | **0.7362** | **+0.051** | **40/50** | **BETTER** |
| C: drop `min_iat` | task 1 | 0.7711 | +0.001 | 7/50 (mostly ties) | INCONCLUSIVE |

Variant B, per class: facebook +0.038, google +0.038, instagram +0.057, mozilla +0.040, x +0.037,
youtube +0.094. Every class improves. Majority-vote flows: 25 fixed, 8 broken. Biggest confusion changes:
x → google 30 → 4, youtube → google 147 → 109, x → mozilla 33 → 16, instagram → facebook 58 → 46;
the one that grows is mozilla → x 33 → 50.

## Confirmation (task 2, fresh folds, and RF as a second model)

Because 007 tested three variants, each winner was re-tested on new folds before adoption.

| cv_seed | Model | Full | Drop 4 (Δ, wins) | Drop 5 (Δ, wins) |
|---|---|---|---|---|
| 2027 | SoftVote | 0.7030 | +0.040, 38 | +0.050, 41 |
| 2027 | RF | 0.6790 | +0.049, 42 | +0.064, 48 |
| 2028 | SoftVote | 0.6937 | +0.035, 37 | +0.051, 41 |
| 2028 | RF | 0.6798 | +0.036, 39 | +0.051, 43 |

All 8 confirmations pass the rule; dropping all five is best every time.

## Caveats

- This is the largest gain so far, but mozilla → x gets worse; timing seems to carry a little of the x vs
  mozilla signal.
- The result holds on this one capture (one phone, 44 minutes). Timing on other networks could behave differently,
  which, if anything, is another reason not to rely on it.
- Task 1 is untouched: timing matters there (Charles: group 0.107).

## Decision

- **Task 2: adopt no-timing features** (`cv.no_timing_features`, 12 columns). Champion is now
  `20260930T170446Z_007_t2_drop_timing5`. `make_submission.py` uses `cv.TASK_FEATURES`; 4 of 81 task 2
  test predictions changed; task 1 predictions are unchanged.
- Task 1: keep `min_iat` (no effect either way).

## Next

- Tell Charles: this is his permutation result turned into a confirmed gain.
- Task 2 feature tests (#5 packet-size CV, #4 direction fractions) now run on top of the no-timing set.
- Look at the mozilla → x increase with the new champion as reference.
