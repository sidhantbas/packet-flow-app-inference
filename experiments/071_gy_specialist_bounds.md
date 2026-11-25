---
title: "071: Google-vs-youtube specialist with the largest-packet bounds (post hoc from 070)"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for using the 070 bound columns only in a google-vs-youtube decision stage, in Task 1 and Task 2, with control arms without the bounds.
source:
  - 070_largest_up_packet_bounds.md
  - 013_gy_specialist.md
  - 062_task1_nonmeta_thresholds.md
experiment:
  id: '071'
  tasks:
  - task1
  - task2
  lever: hierarchy
  status: rejected
  verdict: 'Google-vs-youtube specialist with the bounds: Task 1 -0.0055, Task 2 +0.0009; fails at seed 2026'
---

# 071: Google-vs-youtube specialist with the largest-packet bounds

**Status: done 2026-10-09. Protocol frozen (`fa9caeb`) before any code change or run.**
**Verdict: no test arm is BETTER on 2026 (T1SB −0.0055, T2SB +0.0009); both fail the frozen rule; no confirmation runs. Not adopted.** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: "yes freeze and run 071".

## Origin: post hoc

From [070](070_largest_up_packet_bounds.md): the bound columns raised youtube F1 on every seed in both tasks (Task 2 flow-level
youtube +0.017, interval above zero) but, as general columns, cost facebook and (Task 2) mozilla. Limiting them to the
google-vs-youtube decision is meant to keep the youtube gain without touching other classes. Chosen after seeing 070,
so the test arms must be BETTER on **all five seeds**.

## Frozen arms

After the unchanged production prediction of the task, every flow predicted **google or youtube** is re-decided by a
specialist: a balanced `models.SoftVote` trained only on the google and youtube rows of the training fold. Flows predicted
as any other class are never touched, and no flow can move to or from facebook, instagram, mozilla or x.

| Arm | Task | Specialist columns |
|---|---|---|
| **T1S0** (control) | Task 1 | the 34 production columns |
| **T1SB** | Task 1 | the 34 production columns + `p5_up_max_lo`, `p5_up_max_hi` (070) |
| **T2S0** (control) | Task 2 | the 12 production no-timing columns |
| **T2SB** | Task 2 | the 12 production columns + `up_max_lo`, `up_max_hi` (070, Task 2's own columns) |

The production model of each task is trained on its unchanged production columns only.

## Frozen decision rules

- All four arms on cv_seed 2026 vs production of their task (`20261001T173854Z_034_meta_gate`,
  `20260930T173836Z_014_fi_same_nocw`).
- A test arm (T1SB, T2SB) that is BETTER on 2026 runs on 2027-2030 (Task 1 references from 062; Task 2 references:
  `…014_fi_same_nocw_s2027`, `…_s2028`, and production re-runs on 2029, 2030 created here). **Pass:** BETTER on all five.
  A test arm that is not BETTER on 2026 fails; no confirmation runs.
- Attribution, reported for every seed run: test arm vs its control (`runs.py compare`).
- Evidence only: youtube/google flow-level check (`src/flowcheck.py --apps youtube,google`).
- A pass is a submission candidate (user's approval needed; ranked file chosen on CV before any score is seen).

## Boundaries

Task 2 reads only its own files. Train+validation only. Production frozen at 5eb9a8b until the user approves.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `fa9caeb`, before any code change or run |
| 2026-10-09 | Runner committed; smoke test on one split | `e9d023d`; production keeps its production columns; the specialist changes only google/youtube calls (Task 1: 9 / 4 changes; Task 2: 0) |
| 18:50-18:51 | T1S0, T1SB, T2S0, T2SB on cv_seed 2026 | runs `20261009T185044Z_071_T1S0`, `…185100Z_071_T1SB`, `…185109Z_071_T2S0`, `…185118Z_071_T2SB` |

No deviation from the frozen protocol.

## Results (cv_seed 2026, vs production of the task)

| Arm | Δ macro F1 | Wins / losses / ties | Verdict | google | youtube |
|---|---:|---|---|---:|---:|
| T1S0 (control) | −0.0070 | 15 / 28 / 7 | INCONCLUSIVE | −0.012 | −0.030 |
| T1SB | −0.0055 | 14 / 29 / 7 | INCONCLUSIVE | −0.011 | −0.022 |
| T2S0 (control) | −0.0005 | 10 / 12 / 28 | INCONCLUSIVE | −0.004 | +0.001 |
| T2SB | +0.0009 | 15 / 12 / 23 | INCONCLUSIVE | −0.003 | +0.009 |

Attribution (test arm vs its control, `runs.py compare`): Task 1 +0.0015 (17 / 12, INCONCLUSIVE), Task 2 +0.0014 (14 / 6, BETTER vs the control); the bounds help a little inside the
specialist, but the specialist itself is no better than production's own decision.

## Interpretation

- Task 1: a google-vs-youtube specialist is worse than production's ensemble (as 013 found without the bounds); the bounds
  reduce, but do not remove, that loss.
- Task 2: the specialist changes little; with the bounds youtube gains (+0.009) and macro F1 is +0.0009, far from rule v2.
- The youtube information in the bounds (070) is real but small; neither general columns (070) nor a pair stage (071) turns
  it into a confirmed macro-F1 gain.

## Decision

Not adopted; google ↔ youtube is closed for today. Production unchanged.
