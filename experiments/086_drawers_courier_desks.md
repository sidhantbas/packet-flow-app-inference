---
title: "086: Drawers (google/youtube sub-types) and courier desks (TCP/QUIC) for non-Meta decisions"
created: 2026-10-10
creator: sidhantbas
description: Frozen protocol and results for two untested ways to sharpen the non-Meta decisions in both tasks, each as a desk that re-decides the production model's google/mozilla/x/youtube calls, with a plain desk as control.
source:
  - 085_pair_verifier_sweep.md
  - 084_pair_verifiers.md
  - 044_facebook_subtypes.md
  - 013_google_youtube_specialist.md
experiment:
  id: 086
  tasks:
  - task1
  - task2
  lever: hierarchy
  status: rejected
  verdict: 'Google/youtube sub-types and TCP/QUIC desks: Task 1 -0.015 to -0.022, Task 2 within +-0.002'
---

# 086: Drawers and courier desks for non-Meta decisions

**Status: done 2026-10-10. Protocol frozen (`925665e`) before any code change or run.**
**Verdict: rejected at stage 1. Task 1: every desk worse (−0.015 to −0.022); Task 2: within ±0.002. Drawers and courier desks add nothing over a plain desk.** Results are below.
Do not edit the frozen sections after execution starts. User 2026-10-10: "yes go ahead with drawers and courier desks"
(BACKLOG ready idea 3, sub-type classes for google and youtube; courier desks proposed 2026-10-09). No captures.

## Idea in clerk terms

- **Drawers:** google (and youtube) letters are a mix of very different kinds. Sorting them into a few drawers of similar
  letters lets the clerk learn several sharp ideas instead of one blurry one; every drawer still answers its app.
- **Courier desks:** TCP and QUIC letters are packed by different rules; one desk per courier learns its own habits.

## Frozen arms (each task; production features: Task 1 34 columns, Task 2 12 no-timing columns, Task 2 files only)

A **desk** re-decides the base model's calls of google, mozilla, x or youtube. It outputs only those four labels; facebook and
instagram calls are never touched. Base: Task 1 = production `models.task1_pair_verifiers` (084 ALL), Task 2 = production
`models.task2_model`. In Task 1, flows whose call a 084 verifier changed (084 call ≠ 034 call) are left alone.

| Arm | Desk |
|---|---|
| **N0** (control) | one balanced `SoftVote` trained on the training fold's google, mozilla, x and youtube rows |
| **DR** (drawers) | as N0, but google rows split into 3 drawers and youtube rows into 2 by `KMeans(n_init=10, random_state=seed)` on that app's training rows (log1p of the columns clipped at 0, standardised on those rows); class weights = app-level balanced weights (each drawer row carries its app's weight n / (4 n_app)); predicted drawers map back to their app |
| **CO** (courier desks) | two balanced `SoftVote` desks: one trained on the non-Meta TCP rows, one on the non-Meta UDP rows (`transport` column); each flow goes to its courier's desk |

## Stage 1 (cv_seed 2026, base out-of-fold predictions; per task and arm)

Gate (as 083-085): macro F1 (mean over repeats) > base **and** errors removed ≥ 2 × correct calls broken. DR and CO also
report their difference from N0 and go to stage 2 only if their stage-1 macro F1 is above N0's (otherwise the gain belongs to
the desk, not to the idea). N0 goes to stage 2 if it passes the gate.

## Stage 2

Through `cv.evaluate` / `runlog` vs the task's base on cv_seeds 2026-2030 (references: Task 1 084 ALL runs for each seed; Task 2
champion, `014_fi_same_nocw_s2027/_s2028`, `085_t2_production_s2029/_s2030`). Pass: rule v2 BETTER on all five seeds (ideas
chosen after many results, so five seeds). Several passes in a task: largest mean Δ. For a pass: build the test file (test
features only), official loader, count differences from the 88.11 file. Only a pass whose file differs is a submission candidate
(one submission left; user approval).

## Boundaries

Train+validation only for model choice; test features only to build files; Task 2 reads only Task 2 files; nothing pretrained;
no captures; no capture time or order. Production changes need the user's approval.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-10 | Protocol frozen and committed | before any code change or run |
| 2026-10-10 | Runner committed | `exp086_desks.py` |
| 2026-10-10 | Stage 1 (both tasks, all arms) | no arm passes the gate (`experiments/086_evidence/stage1.json`); no stage 2 |

No deviation from the frozen protocol.

## Results

### Stage 1 (cv_seed 2026; base: Task 1 084 ALL 0.8371, Task 2 production 0.7692; macro F1 mean over repeats)

| Task | Arm | Macro F1 | Δ vs base | Δ vs N0 | Calls changed | Errors removed | Correct calls broken | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | N0 (plain desk) | 0.8222 | −0.0150 | | 223 | 63 | 129 | ❌ |
| 1 | DR (drawers) | 0.8172 | −0.0199 | −0.0050 | 290 | 82 | 168 | ❌ |
| 1 | CO (courier desks) | 0.8149 | −0.0222 | −0.0073 | 268 | 61 | 162 | ❌ |
| 2 | N0 (plain desk) | 0.7701 | +0.0009 | | 23 | 6 | 6 | ❌ |
| 2 | DR (drawers) | 0.7703 | +0.0011 | +0.0002 | 37 | 15 | 13 | ❌ |
| 2 | CO (courier desks) | 0.7678 | −0.0013 | −0.0022 | 29 | 9 | 18 | ❌ |

## Verdict

**Rejected; no stage 2.**

- **Task 1:** every desk is worse than production. A single SoftVote re-deciding the non-Meta calls breaks about twice as
  many right answers as it fixes. Production's two experts (whole flow + opening) already decide these apps better than one
  desk can. Drawers and courier desks make the desk worse still (−0.005 and −0.007 vs N0).
- **Task 2:** changes are tiny (23-37 calls in 3,300) and balanced between fixed and broken. Drawers add +0.0002 over the
  plain desk, which is noise.
- **What it means:** the blurry google class is not the problem. The clerks already separate the kinds of google letters
  they can see, and the letters they confuse look alike on the card whichever drawer or courier desk sorts them (074, 079).
  BACKLOG ready idea 3 (sub-type classes for google and youtube) is closed.
