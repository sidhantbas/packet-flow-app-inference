---
title: '014: Facebook-vs-Instagram specialist'
created: 2026-09-30
creator: sidhantbas
description: Does a second-stage facebook/instagram model improve either task?
experiment:
  id: '014'
  tasks:
  - task1
  - task2
  lever: hierarchy
  status: adopted
  verdict: 'Unweighted facebook/instagram stage: Task 2 +0.018 (18/1/31; facebook +0.026, instagram +0.083), rule v2 on 3 seeds; Task 1 hurts facebook (-0.05 to -0.08)'
  production: Task 2 model (models.task2_model)
---
# 014: Facebook-vs-Instagram specialist

- **Date:** 2026-09-30
- **Question:** Does a second-stage facebook/instagram model improve either task?
- **Status:** done; **task 2 adopted** under rule v2
- **Script:** `src/exp014_fb_ig_specialist.py` (reuses `PairSpecialist` from 013 with pair = facebook/instagram)
- **Runs:** `results/*_014_*` (4 main + 6 confirmation)
- **Reference:** champions

## Hypothesis

Task 2: balanced weights push the first-5 pattern shared by 13 Instagram + 2 Facebook flows to Facebook (012).
An unweighted pair-only model should give it back to Instagram while the balanced base model keeps Facebook
recall elsewhere. Task 1: timing is the Facebook signal (010), so the specialist also gets timing ratios.

## Results (vs champion, cv_seed 2026)

| Variant | Task 1 Δ (W/L/T) | Task 2 Δ (W/L/T) | Task 2 facebook / instagram |
|---|---|---|---|
| fi_same_cw | −0.009 (4/…) | −0.001 (1/…) | |
| **fi_same_nocw** | −0.007 (5/10/35), facebook −0.047 | **+0.018 (18/1/31)** | **+0.026 / +0.083** |
| fi_extra_cw | −0.013 (5/…) | +0.000 (1/…) | |
| fi_extra_nocw | −0.014 (3/…) | +0.019 (19/…) | |

## Confirmation, task 2 (fresh folds, vs the champion re-run on the same folds)

| Variant | cv_seed | Δ | W/L/T | facebook | instagram | flows fixed / broken |
|---|---|---|---|---|---|---|
| fi_same_nocw | 2026 | +0.018 | 18/1/31 | +0.026 | +0.083 | — |
| fi_same_nocw | 2027 | +0.021 | 19/0/31 | +0.040 | +0.088 | 4 / 0 |
| fi_same_nocw | 2028 | +0.015 | 15/0/35 | +0.021 | +0.071 | 3 / 0 |
| fi_extra_nocw | 2027 | +0.020 | 18/0/32 | +0.038 | +0.084 | 4 / 0 |
| fi_extra_nocw | 2028 | +0.014 | 15/1/34 | +0.019 | +0.062 | 3 / 0 |

Across three fold sets, `fi_same_nocw` wins 52 folds and loses 1; every other fold ties. The extra features add
nothing, so the simpler `fi_same_nocw` is the candidate.

## Caveats

- Under the current rule (Δ > 0 and ≥ 35/50 wins) this is **inconclusive**. The rule counts ties as non-wins,
  and a change that only touches facebook/instagram flows leaves ~30 of 50 folds unchanged, so it can never
  reach 35 wins however consistent it is.
- The gain is 3–4 flows per fold set. It is small but has the same sign every time.
- Task 1: every variant hurts Facebook (−0.047 to −0.081). Rejected for task 1.

## Rule v2 (decided by the user on 2026-09-30)

"Better" = mean Δ > 0, ≥ 70% of **non-tied** folds won, ≥ 10 non-tied folds, and the same verdict on cv_seeds
2027 and 2028. It keeps the 70% bar of 35/50 but ignores folds where nothing changed. `runs.py rejudge`
re-evaluated every earlier comparison: 13 verdicts change. The only new BETTER outside 014 is 012's unweighted
SoftVote on task 2 (24/5/21).

## Follow-up: 012 unweighted vs 014 specialist (task 2)

| cv_seed | cw_none vs champion | specialist vs cw_none (head to head) |
|---|---|---|
| 2026 | +0.012 (24/5), BETTER | +0.006 (9/9), facebook +0.031 |
| 2027 | +0.015 (25/…), BETTER | +0.007 (14/10), facebook +0.031 |
| 2028 | +0.008 (20/…), BETTER | +0.007 (12/7), facebook +0.026 |

Both pass. The specialist is ahead on all three fold sets (not decisive on its own). It is chosen because it has
the larger gain and changes only facebook/instagram decisions; the other classes keep balanced weights.

## Decision

- **Task 2: adopt `fi_same_nocw`** as `models.task2_model` (`PairSpecialist`, pair facebook/instagram,
  unweighted specialist on the champion columns). Champion: `20260930T173836Z_014_fi_same_nocw` (0.7544).
  `014_production_check` shows `TASK_FEATURES` + `TASK_MODELS` reproduce both champions on every fold.
- The rebuilt submission has **0 changed test predictions** (the change moves 3–4 CV flows per fold set).
- Task 1: reject (every variant hurts Facebook).
