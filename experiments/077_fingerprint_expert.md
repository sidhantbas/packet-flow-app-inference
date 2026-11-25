---
title: "077: The opening-fingerprint view (076 V3) as a separate expert in Task 1"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for adding a SoftVote on the 076 V3 opening-fingerprint columns as an extra expert inside the production Meta-gate model, alone and together with the rest-of-flow expert.
source:
  - 076_view_screen.md
  - 065_task1_rest_expert.md
  - 028_two_clerks.md
experiment:
  id: '077'
  tasks:
  - task1
  lever: model
  status: inconclusive
  verdict: Fingerprint expert alone WORSE on 5 seeds; fingerprint + rest-of-flow experts BETTER on 4/5; same test file as 87.77
---

# 077: The opening-fingerprint view as a separate expert in Task 1

**Status: done 2026-10-09. Protocol frozen (`fb3de74`) before any code change or run.**
**Verdict: F WORSE on all five seeds. FR BETTER on 4 of 5 (2027 NEAR-MISS, 68%) and mean +0.0062 below 065 R's +0.0066: fails the frozen rule; not adopted under this protocol.** Results are below.
Do not edit the frozen sections after execution starts. Chosen from the 076 screen (post hoc), so arms need **BETTER on all
five seeds**.

## Frozen arms

Production MetaGate; its experts and gate keep exactly the 34 production columns. Extra balanced `models.SoftVote` experts are
averaged into `p` (in `MetaGate.predict`, `p = mean(whole-flow, opening, extra experts)`); all later rules unchanged.

| Arm | Extra experts |
|---|---|
| **F** | V3 opening fingerprint (13 columns, `exp076_view_screen.view_table`, prefix `v3_`) |
| **FR** | V3 fingerprint and the 065 rest-of-flow expert (11 `r_*` columns) |

## Frozen decision rules

- Each arm on cv_seeds 2026-2030 vs production on the same seed (`20261001T173854Z_034_meta_gate`,
  `20261009T172902Z_062_production_s2027`, `…173025Z…s2028`, `…173146Z…s2029`, `…173307Z…s2030`).
- **Pass:** rule v2 BETTER on all five seeds. FR must also have a mean Δ over the five seeds above 065 R's (+0.0066).
- Also reported (evidence): pooled wins, per-class Δ, flow-level check for facebook/instagram and youtube/google.
- A pass is a submission candidate; the ranked file is decided on CV before any score is seen; the user approves.

## Boundaries

Train+validation only; Task 1 may read Task 2 files (022, disclosed). Production frozen at 5eb9a8b until the user approves.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `fb3de74`, before any code change or run |
| 2026-10-09 | Runner committed; smoke test on one split | `9af50ff`; without extra experts it reproduces production; F / FR change 4 / 3 of 165 predictions, none touching Meta |
| 20:09-20:12 | F and FR on cv_seeds 2026-2030 vs production | runs `results/*_077_F[_s<seed>]`, `results/*_077_FR[_s<seed>]` |
| after the runs | FR vs 065 R per seed; flow checks pooled over five seeds | `experiments/077_evidence/flowcheck_FR_*.md` |

No deviation from the frozen protocol.

## Results (vs production on the same seed)

| Seed | F Δ (wins / losses) | F verdict | FR Δ (wins / losses) | FR verdict | FR youtube | FR google | FR facebook |
|---|---|---|---|---|---:|---:|---:|
| 2026 | −0.0131 (6 / 38) | WORSE | +0.0058 (24 / 9) | BETTER | +0.021 | +0.007 | +0.000 |
| 2027 | −0.0119 (8 / 39) | WORSE | +0.0044 (19 / 9) | NEAR-MISS | +0.013 | +0.001 | −0.002 |
| 2028 | −0.0095 (12 / 32) | WORSE | +0.0064 (22 / 6) | BETTER | +0.016 | +0.007 | +0.000 |
| 2029 | −0.0118 (10 / 36) | WORSE | +0.0073 (26 / 8) | BETTER | +0.022 | +0.009 | +0.004 |
| 2030 | −0.0105 (12 / 35) | WORSE | +0.0072 (20 / 3) | BETTER | +0.021 | +0.006 | +0.011 |

FR over five seeds: mean +0.0062; pooled non-tied wins 111 / 146 = 76%; facebook mean +0.0026.
FR vs 065 R (same seed): +0.0004, −0.0007, −0.0003, −0.0024, +0.0013 (all INCONCLUSIVE; mean −0.0003).

Flow-level check, FR vs production, pooled over five seeds (evidence only): youtube F1 +0.018 [+0.006, +0.035] **better**;
google F1 +0.006 [+0.001, +0.012] **better**; facebook +0.002 [−0.001, +0.008] and instagram +0.001 [−0.001, +0.003]
unproven; McNemar on youtube/google flows fixed 1, broken 0.

## Interpretation

- The fingerprint expert alone (F) hurts on every seed: averaged in with equal weight, its opening-only view pulls
  whole-flow decisions toward the opening.
- Together with the rest-of-flow expert (FR) it is the most consistent change measured so far: BETTER on four seeds, 76% of
  non-tied folds, and flow-level gains for youtube and google whose intervals lie above zero, with Meta untouched.
- Its average gain equals 065 R's (FR vs R about zero): the fingerprint adds consistency, not size. Expected test effect
  about +0.3 points, inside the 81-flow noise.

## Decision

Under this protocol: not adopted (2027 near miss; mean not above 065 R's). FR meets the 066 exception criteria (Δ > 0 on
all seeds, mean ≥ +0.004, pooled wins ≥ 62%, facebook ≥ 0) with better consistency than 066; adopting it would be a
documented exception that only the user can decide.
