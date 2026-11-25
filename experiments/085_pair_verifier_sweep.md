---
title: "085: Pair-verifier sweep over the remaining separable confusions (Task 1 and Task 2)"
created: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for applying the 083/084 verifier method to every remaining confusion cell that the 079 audit lists with a pair SoftVote AUC of at least 0.95, in both tasks.
source:
  - 084_pair_verifiers.md
  - 083_instagram_google_verifier.md
  - 079_pipeline_audit.md
experiment:
  id: 085
  tasks:
  - task1
  - task2
  lever: hierarchy
  status: rejected
  verdict: 'Verifier sweep over 9 more separable pairs: none passes; Task 2 mozilla verifier 55 W / 0 L but BETTER on 4/5'
---

# 085: Pair-verifier sweep over the remaining separable confusions

**Status: done 2026-10-09. Protocol frozen (`80bd596`) before any code change or run.**
**Verdict: no pass. T2-MG (Task 2 mozilla calls vs google) 55 wins / 0 losses but BETTER on 4 of 5 seeds; test file unchanged. Eight cells fail stage 1.** Results are below.
Do not edit the frozen sections after execution starts. User 2026-10-09: "tell me we can go more higher like this". The
direction (extend the verifier method to every remaining separable cell) follows 084's CV result; the sixth submission's score
(88.11) is information only and plays no part in choosing cells, settings or decisions.

## Candidate cells (fixed now: every 079 top-10 cell with pair SoftVote AUC ≥ 0.95 not tested in 083/084)

A verifier re-decides production's calls of one class with a balanced `models.SoftVote` trained only on the two classes' rows of
the training fold (production features: Task 1 34 columns `cv.task1_with_prefix_features`; Task 2 12 columns
`cv.no_timing_features`, Task 2 files only).

| Id | Task | Cell (true → called) | Re-decides calls of | Between | 079 AUC |
|---|---|---|---|---|---:|
| T1-YI | 1 | instagram → youtube | youtube | instagram vs youtube | 0.96 |
| T1-FG | 1 | google → facebook | facebook | facebook vs google | 0.99 |
| T1-XF | 1 | facebook → x | x | facebook vs x | 0.98 |
| T2-XF | 2 | facebook → x | x | facebook vs x | 0.98 |
| T2-XM | 2 | mozilla → x | x | mozilla vs x | 0.95 |
| T2-XY | 2 | youtube → x | x | x vs youtube | 0.97 |
| T2-YI | 2 | instagram → youtube | youtube | instagram vs youtube | 0.97 |
| T2-GM | 2 | mozilla → google | google | google vs mozilla | 0.99 |
| T2-MG | 2 | google → mozilla | mozilla | google vs mozilla | 0.99 |

Task 1 verifiers sit on top of 084 ALL (the current best Task 1 model); Task 2 verifiers on top of production `models.task2_model`.
Verifiers always act on the base model's original call, so they never chain.

## Stage 1 (cv_seed 2026, out-of-fold predictions of the base model; per verifier)

Gate (as in 083/084): macro F1 (mean over repeats) > base **and** errors removed ≥ 2 × correct calls broken.
If two passing verifiers re-decide the same call class, only the one with the larger stage-1 Δ is kept.

## Stage 2 (per task: each passing verifier, and the stack of all kept verifiers if more than one passes)

Through `cv.evaluate` / `runlog` vs the task's base on cv_seeds 2026-2030 (a sweep over nine cells is post hoc, so all five
seeds, as for 062/066). Pass: rule v2 BETTER on all five. If several arms pass in a task, the largest mean Δ wins. For a pass:
build the test file (test features only), official loader, count differences from the 88.11 file (084 ALL). Only a pass whose
file differs is a submission candidate (user approval; one submission left).

## Boundaries

Train+validation only for model choice; test features only to build files; Task 2 reads only Task 2 files; nothing pretrained;
no capture time or order. Production frozen at 5eb9a8b until the user approves.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | before any code change or run |
| 2026-10-09 | Stage-1 script committed and run | `exp085_stage1.py`; only T2-MG passes (`experiments/085_evidence/stage1.json`) |
| 2026-10-09 | Stage-2 runner committed | `95d86f8` |
| 22:1x | First stage-2 batch | **failed before any run** (zsh does not word-split `$P`); no run folder written; rerun with explicit commands |
| 22:15-22:16 | T2-MG on 2026-2030; production Task 2 references for 2029/2030 | runs `20261009T221508Z_085_T2MG`, `…221524Z…_s2027`, `…221538Z…_s2028`, `…221555Z…_s2029`, `…221611Z…_s2030`; refs `…221546Z_085_t2_production_s2029`, `…221602Z_085_t2_production_s2030`; 2026-2028 refs: champion and `014_fi_same_nocw_s2027/_s2028` |
| after the runs | Test file built for information (outside the protocol, which builds files only for a pass) | identical Task 2 predictions to the 88.11 file |

## Results

### Stage 1 (cv_seed 2026; base: Task 1 084 ALL 0.8371, Task 2 production 0.7692, macro F1 mean over repeats)

| Id | Δ | Changed | Removed | Broken | Gate |
|---|---:|---:|---:|---:|---|
| T1-YI | −0.0028 | 7 | 0 | 5 | ❌ |
| T1-FG | −0.0160 | 27 | 3 | 18 | ❌ |
| T1-XF | −0.0013 | 2 | 0 | 2 | ❌ |
| T2-XF | 0.0000 | 0 | 0 | 0 | ❌ |
| T2-XM | 0.0000 | 0 | 0 | 0 | ❌ |
| T2-XY | 0.0000 | 0 | 0 | 0 | ❌ |
| T2-YI | −0.0010 | 6 | 0 | 0 | ❌ |
| T2-GM | 0.0000 | 0 | 0 | 0 | ❌ |
| **T2-MG** | **+0.0029** | 13 | 10 | 0 | ✅ |

### Stage 2: T2-MG vs production Task 2 (rule v2)

| Seed | Δ | W / L / T | Verdict | google | mozilla |
|---|---:|---|---|---:|---:|
| 2026 | +0.0028 | 11 / 0 / 39 | BETTER | +0.003 | +0.013 |
| 2027 | +0.0026 | 11 / 0 / 39 | BETTER | +0.004 | +0.012 |
| 2028 | +0.0020 | 8 / 0 / 42 | **INCONCLUSIVE** (8 non-tied < 10) | +0.002 | +0.010 |
| 2029 | +0.0034 | 14 / 0 / 36 | BETTER | +0.005 | +0.015 |
| 2030 | +0.0025 | 11 / 0 / 39 | BETTER | +0.003 | +0.012 |

Pooled 55 wins, 0 losses; mean Δ +0.0027; other classes unchanged. Test file: identical Task 2 predictions to the 88.11 file.

## Verdict

**No pass under the frozen rule.** T2-MG never loses a fold (55 / 0) but is BETTER on four of five seeds: on 2028 only 8 folds
differ, below rule v2's minimum of 10. Its mean Δ (+0.0027) is also below the 066 exception threshold (+0.004). Whatever is
decided about it, it changes no test prediction, so it cannot move the score. The other eight cells fail stage 1: production
already gets those calls right, so the verifiers break more than they fix (Task 1) or change nothing (Task 2, where many
openings are exact duplicates). The verifier method is exhausted on the separable cells listed by 079.
