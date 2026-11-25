---
title: "057: Captured flows only in the Facebook-vs-Instagram decision, and a low dose"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for two narrower uses of the captured flows in Task 1, judged by rule v2 on the original flows.
source:
  - 056_capture_augmentation.md
  - 055_long_sessions.md
  - 014_fb_ig_specialist.md
experiment:
  id: '057'
  tasks:
  - task1
  lever: data
  status: rejected
  verdict: 'Captured flows only in the facebook/instagram decision (-0.043) or as a 10% dose (-0.026): worse'
---

# 057: Captured flows only in the Facebook-vs-Instagram decision, and a low dose

**Status: done 2026-10-09. Protocol frozen (`4a80ef8`) before any code change or run.**
**Verdict: all three arms WORSE on cv_seed 2026 (S0 −0.023, S1 −0.043, D10 −0.026); S1 vs S0 −0.020. Stop using captured flows for training.** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: "okay conduct the experiment" (ideas 1
and 2 of the brainstorm after [056](056_capture_augmentation.md)); the user's gate override of 056 applies here too.

## Question

Can the captured flows help Task 1 if they never compete with google, x, youtube or mozilla flows?

## Evidence before this experiment

- [056](056_capture_augmentation.md): captured flows in the whole training fold: −0.084 / −0.072. Damage came from
  google/x/youtube/mozilla flows being called facebook (google → facebook 10 → 96).
- [055](055_long_sessions.md): captured Meta flows match the training records on sizes, counts and (with 20-min sessions)
  most timing columns; facebook `mean_iat` stays inconsistent; opening (prefix-5) sizes carry the iPhone signature.
- Experiment 014: a facebook/instagram specialist (original rows only) **hurt** Task 1 Facebook (−0.047 to −0.081).
  Hence the control arm S0 below.
- Production counts (056 report, 50 folds): facebook → instagram 22, instagram → facebook 26.

## Frozen arms

| Arm | Model | Captured rows |
|---|---|---|
| **S0** (control) | Production `task1_meta_gate`; then every row it calls facebook or instagram is re-decided by a facebook-vs-instagram specialist | none |
| **S1** | As S0 | captured facebook (62) and instagram (87) rows **in the specialist only**; the production model never sees them |
| **D10** | Production `task1_meta_gate` | a random 10% of the captured facebook and instagram rows (6 and 9 rows; new draw per fold, seed = fold index) in the whole training fold |

Specialist: balanced `SoftVote` (RF + ExtraTrees + LightGBM) trained on the facebook and instagram rows of the training
fold (+ captured rows in S1), on **15 columns**: the 16 gate-2 columns (`capture_checks.PROX_COLS`) without `mean_iat`
(inconsistent for facebook in 055). No `min_iat`, no prefix-5 (`p5_`) columns (iPhone signature).

Captured data: exactly the 056 rows (`data/captures/056-augmentation/`, `--split-merged`, session labels).

## Frozen decision rules

- Each arm vs the Task 1 champion `20261001T173854Z_034_meta_gate`, cv_seed 2026, rule v2.
- **S1 vs S0** (`runs.py compare`): shows the effect of the captured rows themselves.
- A candidate needs BETTER vs production on 2026 **and** on 2027-2030 (production re-run on each seed as reference).
  Confirmation seeds only for an arm that passes on 2026. For S1, also report S1 vs S0 on every seed run.
- If no arm passes on 2026: stop using captured flows for training (056 restart point).
- Adoption still needs the user's approval and a report entry (outside data, Task 1 only).

## Boundaries

Task 1 only. Original data: train+validation only. Held-out flows always original. Production frozen at 5eb9a8b.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `4a80ef8`, before any code change or run |
| 2026-10-09 | Runner committed; smoke test on one split | `81cc993`; S1: production model trained on original rows only, specialist gets 149 captured rows; D10 adds 6 + 9 rows |
| 13:36-13:37 | S0, S1, D10 on cv_seed 2026 | runs `20261009T133655Z_057_S0`, `20261009T133711Z_057_S1`, `20261009T133725Z_057_D10` |

No deviation from the frozen protocol. No arm passed on 2026, so no confirmation seeds were run (frozen rule).

## Results

| Arm | Macro F1 | Δ vs production (0.8277) | Wins / losses / ties | facebook Δ | instagram Δ | Verdict |
|---|---:|---:|---|---:|---:|---|
| S0 specialist, no captures | 0.8048 | −0.0229 | 5 / 20 / 25 | −0.109 | −0.028 | WORSE |
| S1 specialist + captures | 0.7848 | −0.0429 | 6 / 27 / 17 | −0.226 | −0.031 | WORSE |
| D10 low dose | 0.8015 | −0.0262 | 12 / 37 / 1 | −0.171 | −0.024 | WORSE |

**S1 vs S0** (effect of the captured rows alone, `runs.py compare`): Δ −0.0200, 7 wins / 21 losses, facebook −0.117.

Confusion changes (50 folds summed): S0 facebook → instagram 22 → 38; S1 facebook → instagram 22 → 55;
D10 google → facebook 10 → 32 and x → facebook 1 → 12.

D10 side effect (not a frozen measurement): non-Meta classes improve (mozilla +0.023, 14 wins / 0 losses; youtube
+0.013; google +0.004; youtube → google 91 → 81), as in 056 (youtube → google 91 → 68).

## Interpretation

- S0 repeats experiment 014: a facebook/instagram specialist hurts Task 1 (the production two-clerks and Meta-gate rules
  already make this decision better).
- Captured rows hurt even where they meet only facebook and instagram (S1 vs S0 −0.020): the captured facebook flows
  look more like original instagram flows than like original facebook flows, so the specialist sends real facebook
  flows to instagram (22 → 55).
- Even a 10% dose costs facebook −0.17 (only this dose was tested).
- The non-Meta gains in D10 and 056 are a post-hoc observation, not tested by a frozen rule.

## Decision

Stop using captured flows for training (056 restart point confirmed). Production unchanged (5eb9a8b).
Captured data stays useful for the report: an out-of-distribution check and the documented capture pipeline.
