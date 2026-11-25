---
title: "084: Pair verifiers for other cleanly separable confusions (google vs x, google vs mozilla)"
created: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for extending the 083 method (re-check one app's calls against a rival the data separates almost perfectly) to x and mozilla calls (rival google) and google calls (rival mozilla), alone and stacked with 083.
source:
  - 083_instagram_google_verifier.md
  - 079_pipeline_audit.md
experiment:
  id: 084
  tasks:
  - task1
  lever: hierarchy
  status: adopted
  verdict: 'Adds a google-vs-x verifier for x calls (ALL = 083 + VX): BETTER on all 5 seeds (mean +0.0050), facebook unchanged; production 9-10 Oct (88.11)'
  production: Google-vs-x verifier; Task 1 production 9-10 Oct
---

# 084: Pair verifiers for other cleanly separable confusions

**Status: done 2026-10-09. Protocol frozen (`87ab548`) before any code change or run.**
**Verdict: VX and ALL (083 + VX) pass; ALL BETTER on all five seeds (mean +0.0050); test file differs from 87.77 in one flow. VM, VG fail stage 1.** Results are below.
Do not edit the frozen sections after execution starts. User 2026-10-09: "we need to level up the score". Follows the only
method that passed rule v2 today (083). Chosen from the 079 audit (pairs with SoftVote AUC ≥ 0.98 that production still
confuses), so stage 2 requires rule v2 on three seeds as in 083.

## Frozen verifiers (Task 1; each a balanced `models.SoftVote` on the two classes' rows of the training fold, 34 production columns)

| Verifier | Re-decides production calls of | Between | Errors it targets (per repeat, 079) |
|---|---|---|---|
| **VX** | x | google vs x | google → x 4.6 |
| **VM** | mozilla | google vs mozilla | google → mozilla 1.5 |
| **VG** | google | google vs mozilla | mozilla → google 2.2 |

Stacked arm **ALL** = 083 (instagram calls vs google) + every verifier that passes its stage-1 gate, applied in the order
083, VX, VM, VG (each to production's original call, so they never chain).

## Stage 1 (cv_seed 2026, production folds; per verifier)

Gate (same as 083): macro F1 (mean over repeats) > production's **and** errors removed ≥ 2 × correct calls broken.

## Stage 2 (passing verifiers, and ALL if at least one passes)

Through `cv.evaluate` / `runlog` on cv_seeds 2026, 2027, 2028 vs production (champion and 062 references). Pass: rule v2 BETTER
on all three. ALL must also beat 083 alone (mean Δ over the three seeds > 0, `runs.py compare`). For each pass: build the test
file (test features only), check it with the official loader and count its differences from the 87.77 file. Only a pass whose
test file differs is a submission candidate (user approval; the ranked file is chosen on CV before any score).

## Boundaries

Train+validation only for model choice; test features only to build files; nothing pretrained. Production frozen at 5eb9a8b
until the user approves.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | before any code change or run |
| 2026-10-09 | Stage 1 (cv_seed 2026, production folds) | VX PASS; VM, VG fail (table below) |
| 2026-10-09 | Runner committed | `b5f4576` |
| 22:03-22:05 | VX and ALL on 2026, 2027, 2028 | runs `20261009T220357Z_084_VX`, `…220413Z…_VX_s2027`, `…220429Z…_VX_s2028`, `20261009T220447Z_084_ALL`, `…220504Z…_ALL_s2027`, `…220522Z…_ALL_s2028` |
| after the runs | ALL vs 083 alone (`runs.py compare`) | BETTER on all three seeds |
| after the runs | Test files built (test features only), official loader | VX and ALL give the same file: 1 Task 1 change vs the 87.77 file |
| 22:06 | Extra evidence, **outside the frozen decision rule**: ALL on 2029, 2030 | runs `20261009T220630Z_084_ALL_s2029`, `20261009T220647Z_084_ALL_s2030` |

No deviation from the frozen protocol; the 2029/2030 runs were added afterwards as evidence only. Runs carry a `dirty-tree`
warning for unrelated local files (`.gitignore`, `.mission*.md`, (unrelated local folder)); code hashes are recorded.

## Results

### Stage 1 (cv_seed 2026, production out-of-fold predictions; production macro 0.8323)

| Verifier | Macro F1 | Δ | Calls changed | Errors removed | Correct calls broken | Gate |
|---|---:|---:|---:|---:|---:|---|
| **VX** (x calls, google vs x) | 0.8346 | +0.0023 | 26 | 19 | 6 | ✅ PASS |
| VM (mozilla calls, google vs mozilla) | 0.8271 | −0.0052 | 26 | 1 | 21 | ❌ fail |
| VG (google calls, google vs mozilla) | 0.8287 | −0.0036 | 34 | 9 | 23 | ❌ fail |

### Stage 2 (rule v2 vs production; ALL = 083 + VX)

| Seed | VX Δ | VX W/L/T | VX verdict | ALL macro F1 | ALL Δ | ALL W/L/T | ALL verdict | ALL vs 083 |
|---|---:|---|---|---:|---:|---|---|---|
| 2026 | +0.0023 | 17 / 5 / 28 | BETTER | 0.8321 | +0.0044 | 24 / 7 / 19 | BETTER | BETTER (+0.0023) |
| 2027 | +0.0024 | 17 / 3 / 30 | BETTER | 0.8336 | +0.0069 | 26 / 5 / 19 | BETTER | BETTER (+0.0023) |
| 2028 | +0.0024 | 22 / 4 / 24 | BETTER | 0.8061 | +0.0040 | 33 / 4 / 13 | BETTER | BETTER (+0.0024) |
| 2029 (extra) | | | | 0.8316 | +0.0030 | 29 / 7 / 14 | BETTER | |
| 2030 (extra) | | | | 0.8313 | +0.0068 | 26 / 3 / 21 | BETTER | |

ALL per class vs production (2026 / 2027 / 2028 / 2029 / 2030): facebook 0 on every seed; google +0.008 / +0.010 / +0.001 /
+0.008 / +0.012; instagram +0.011 / +0.023 / +0.011 / −0.001 / +0.012; x +0.008 / +0.009 / +0.012 / +0.011 / +0.017; mozilla
and youtube 0. Mean Δ over five seeds **+0.0050**, BETTER on all five, 138 wins vs 26 losses (84% of non-tied folds).

### Test file

VX and ALL give the same file. Task 2 is identical to the 87.77 file; Task 1 differs in **one flow**: `flow_000095`, x → google
(the VX verifier; 083 changes no test prediction). Official loader: both formats parse, 81/81 IDs per task, valid labels.
Saved as `submissions/best-88.11-production-084/` (zip SHA-256 `7879c92a…5c7b`, json `319d43b7…2c98`). In stage 1, VX's
changes were right in 19 of 25 decided cases (76%); that is the CV rate for this kind of change, not a statement about this flow.

## Verdict

**VX and ALL pass the frozen protocol; ALL is the best-evidence Task 1 model of the project** (BETTER on all five seeds; the
first candidate since 034 that passes rule v2 and changes the test file). VM and VG are rejected at stage 1: google vs
mozilla separates well as a pair, but production's mozilla and google calls are already mostly right, so a verifier breaks
more than it fixes. Submission candidate: `submissions/best-88.11-production-084/`. By the rule fixed before any score, it
becomes our ranked entry on CV evidence if the user adopts it, whatever it scores; its score is information only and is never
used to infer the label of `flow_000095`. Adoption into production (`models.TASK_MODELS`, `runs.py champion`) needs the user's approval.
