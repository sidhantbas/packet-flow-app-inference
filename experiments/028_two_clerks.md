---
title: '028: "Two clerks" for Task 1'
created: 2026-10-01
creator: sidhantbas
description: Do a whole-run expert and a separate opening expert, combined, beat the Task 1 champion?
experiment:
  id: 028
  tasks:
  - task1
  lever: model
  status: adopted
  verdict: 'Two experts (whole flow + opening), Meta decided by the whole-flow expert: 0.817, +0.005 to +0.013 on 5 seeds but 58-65% wins; adopted as a documented exception'
  production: Task 1 two experts (whole flow + opening)
---
# 028: "Two clerks" for Task 1

- **Date:** 2026-10-01
- **Question:** Do a whole-run expert and a separate opening expert, combined, beat the Task 1 champion?
- **Status:** done; **adopted for Task 1 on 2026-10-01 as a deliberate exception to rule v2 (user decision)**
- **Script:** `src/exp028_two_clerks.py`; `models.TwoClerks`
- **Runs:** `results/*_028_*`
- **Reference:** Task 1 champion (022 model); seeds 2027-2030 vs its re-runs from 023

## Motivation (error decoding, 2026-10-01)

44 of 330 Task 1 flows are wrong in >= 5 of 10 CV repeats. Their 5 nearest neighbours share their app 17% of the
time (73% for other flows); 18 of 44 have all 5 neighbours from another app; the model's wrong label equals the
nearest neighbour's 59% of the time. By app: google 19 (short, median 0.6 s), youtube 13, facebook 5, instagram 4,
mozilla 2, x 1. Accuracy hardly depends on flow size (0.84-0.89) or transport. The Task 2 model gets 22 of the 44
mostly right, and the reverse holds for 22 Task 2-hard flows: the whole-run and opening views fail on different
flows, but the 022 model mixes all 34 columns in one ensemble.

## Setup

Whole-run expert = `task1_model` (022). Opening expert = SoftVote on the 12 prefix-5 columns without timing (Task 2
recipe without its fb/ig stage). Facebook calls of the 17-column model kept in all variants.
- avg, confident: fixed before running.
- avg_meta_whole: added after seeing seed 2026 (Instagram -0.06): the whole-run expert decides whenever either side says
  facebook/instagram. Held to all five seeds.

## Results

| Variant | cv_seed | Macro F1 | Δ | W / L | Notes |
|---|---|---|---|---|---|
| avg | 2026 | 0.806 | -0.001 | 30 / 20 | google +0.028, mozilla +0.024, youtube +0.017, **instagram -0.063** |
| confident | 2026 | 0.804 | -0.002 | 29 / 21 | google +0.028, youtube +0.022, **instagram -0.074** |
| avg_meta_whole | 2026 | **0.817** | +0.011 | 32 / 17 | google +0.019, mozilla +0.024, youtube +0.020; fb/ig unchanged |
| avg_meta_whole | 2027 | | +0.011 | 31 / 19 | |
| avg_meta_whole | 2028 | | +0.005 | 30 / 20 | |
| avg_meta_whole | 2029 | | +0.013 | 31 / 18 | |
| avg_meta_whole | 2030 | | +0.008 | 29 / 21 | |

## Interpretation

The opening expert does fix flows in the large confused classes (google/youtube/mozilla), as the decoding predicted,
but without a facebook/instagram stage it breaks Instagram (shared opening). With Meta decisions left to the whole-run
expert, the gain is positive on all five split sets (+0.005 to +0.013) but wins only 58-65% of folds: a real but
small effect, below the 70% bar. Most of the 22 "rescuable" flows are offset by flows the opening expert breaks.

## Decision

Not adopted (rule v2 not met on any seed). Strongest consistent Task 1 lead together with the TabPFN member (024/026).

## Adoption (2026-10-01, user decision; deliberate exception)

After the error audit (031) and the loss breakdown (most remaining loss is facebook/instagram scarcity, google/youtube overlap
and fold noise that hides gains below ~0.01), the user chose to adopt `avg_meta_whole` although it never reaches 70% wins:
it is positive on all five split sets (+0.005 to +0.013), uses only the given dataset, and leaves facebook/instagram decisions
to the existing whole-run model. Same kind of override as the Task 1 ensemble in 005.

- `models.TASK_MODELS["task1_static"] = task1_two_clerks` (`TwoClerks(mode="avg_meta_whole")`); features unchanged.
- `028_production_check` reproduces `20261001T163334Z_028_two_clerks_avg_meta_whole` on all 50 folds; Task 2 unchanged.
- Task 1 champion: `20261001T163334Z_028_two_clerks_avg_meta_whole` (0.8172).
- Rebuilt submission: 6 Task 1 test predictions differ from the 84.62 file (flow_000007, 000304, 000884, 000906 google → youtube;
  flow_000415 google → mozilla; flow_000095 youtube → x); Task 2 identical. Not submitted.
- Official-scorer pipeline check (train only → validation): Task 1 0.766 (was 0.762), Task 2 0.778, total 77.2 (was 77.0).
