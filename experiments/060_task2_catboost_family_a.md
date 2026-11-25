---
title: "060: Task 2 with unweighted CatBoost and Charles's family A features"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for three Task 2 variants built on two earlier near misses, judged by rule v2 on five seeds.
source:
  - 009_catboost.md
  - 014_fb_ig_specialist.md
  - 027_charles_handoff.md
experiment:
  id: '060'
  tasks:
  - task2
  lever: model
  status: rejected
  verdict: 'Unweighted CatBoost, SoftVote + CatBoost, family A columns (each with the 014 stage): -0.004 / -0.001 / -0.001'
---

# 060: Task 2 with unweighted CatBoost and Charles's family A features

**Status: done 2026-10-09. Protocol frozen (`e7e0fad`) before any code change or run.**
**Verdict: all three arms INCONCLUSIVE and slightly below production (CB −0.0040, SVCB −0.0010, A −0.0008). No submission candidate.** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: "yes start with the task 2 experiment".

## Context

After the third submission (87.77; Task 2 0.905), the user wants to use the remaining submissions. Rule (AGENTS.md,
`.mission.md`): a new submission only for a model that beats production by rule v2 on cross-validation; never choose
between files by leaderboard score.

## Evidence before this experiment

- [009](009_catboost.md): unweighted CatBoost alone on Task 2 (no timing) 0.752, +0.015 (27/50) over the then champion
  SoftVote (0.737); balanced CatBoost worse. Not confirmed.
- [014](014_fb_ig_specialist.md): production Task 2 = balanced SoftVote + unweighted facebook/instagram SoftVote stage,
  CV 0.754; its gain came from instagram.
- 027: family A (size variability and direction shares) helped Charles's ExtraTrees on Task 2
  (+0.007 / +0.012 / +0.008 on three seeds); on our SoftVote the related ratios did nothing (008).

## Frozen arms

All arms keep production's features (`cv.no_timing_features`, 12 Task 2 columns, Task 2 files only) and production's
facebook/instagram stage (unweighted SoftVote trained on facebook + instagram, re-deciding flows the base calls either).

| Arm | Base model (6 classes) | Extra columns |
|---|---|---|
| **CB** | unweighted CatBoost (`models.catboost(class_weight=None)`, defaults) | none |
| **SVCB** | mean of production's balanced SoftVote probabilities and unweighted CatBoost probabilities | none |
| **A** | production's balanced SoftVote | family A from `exp027_handoff.fam_a` on the Task 2 columns: `cv_size_up`, `cv_size_down`, `down_byte_share`, `down_pkt_share`, `no_up`, `no_down` (also given to the stage) |

## Frozen decision rules

- Each arm vs the Task 2 champion `20260930T173836Z_014_fi_same_nocw` on cv_seed 2026, rule v2.
- An arm passes only with BETTER on 2026 **and** on 2027, 2028, 2029, 2030, each against production re-run on the same
  seed (references created by this experiment). Confirmation seeds only for arms that pass on 2026.
- If several pass, choose the one with the largest mean Δ over the five seeds.
- A pass is a submission candidate: Task 2 predictions change, Task 1 stays the frozen file. Submitting needs the user's
  approval; the choice is made on this CV evidence before any new score is seen.

## Boundaries

Task 2 reads only `task2_realtime_prefix5/` files (condition 2). Train+validation only; no test labels.
Production frozen at 5eb9a8b until the user approves a change.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `e7e0fad`, before any code change or run |
| 2026-10-09 | Runner committed; smoke test on one split | `8f705c5`; the SoftVote arm reproduces production's predictions exactly |
| 17:17-17:18 | CB, SVCB, A on cv_seed 2026 | runs `20261009T171757Z_060_CB`, `20261009T171809Z_060_SVCB`, `20261009T171817Z_060_A` |

No deviation from the frozen protocol. No arm passed on 2026, so no confirmation seeds were run.

## Results (vs production Task 2, 0.7544)

| Arm | Macro F1 | Δ | Wins / losses / ties | Verdict |
|---|---:|---:|---|---|
| CB (unweighted CatBoost base) | 0.7504 | −0.0040 | 10 / 23 / 17 | INCONCLUSIVE |
| SVCB (SoftVote + CatBoost base) | 0.7534 | −0.0010 | 12 / 10 / 28 | INCONCLUSIVE |
| A (+ family A columns) | 0.7535 | −0.0008 | 13 / 13 / 24 | INCONCLUSIVE |

Per class, all changes are within ±0.015; the largest are facebook −0.009 to −0.015 and instagram +0.007 (A).

## Interpretation

- The 009 CatBoost lead (+0.015 over the old champion) appears to be already captured by production's facebook/instagram stage:
  combined with the stage, CatBoost adds nothing.
- Family A does nothing on our Task 2 model, as in 008 (it helped only Charles's single ExtraTrees in 027).
- Task 2 production sits at a plateau; with test Task 2 already 0.905 (leader 0.92), the remaining Task 2 upside is small.

## Decision

No change; production Task 2 stays. No new submission from this experiment.
