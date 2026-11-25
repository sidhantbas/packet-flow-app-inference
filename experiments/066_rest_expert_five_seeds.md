---
title: "066: Five-seed check of the rest-of-flow expert (065 arm R) as a candidate for a documented exception"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Pre-registered five-seed evaluation of 065 arm R, with explicit criteria for a user-decided exception like 028 and 034.
source:
  - 065_task1_rest_expert.md
  - 028_two_clerks.md
  - 034_meta_gate.md
experiment:
  id: '066'
  tasks:
  - task1
  lever: model
  status: adopted
  verdict: 'Five-seed check of the rest-of-flow expert: delta > 0 on all seeds (mean +0.0066, 62.2% wins); uploaded as a candidate (about 86); later part of 089'
  production: Rest-of-flow expert (via 089)
---

# 066: Five-seed check of the rest-of-flow expert (065 arm R)

**Status: done 2026-10-09. Protocol frozen (`3b352bb`) after 065 seed 2026 only.**
**Verdict: all four criteria hold (Δ > 0 on 5/5 seeds, mean +0.0066, pooled wins 62.2%, facebook mean +0.006). Candidate for a documented exception; the user decides.** Results are below.
Do not edit the frozen sections after execution starts.

## Why a separate protocol

065 arm R gained +0.0054 on cv_seed 2026 with every non-Meta app up and facebook unchanged, but won 65% of non-tied folds
(70% needed), so 065's rule allowed no confirmation runs. Two production models were adopted as documented exceptions after
consistent five-seed evidence (028: +0.005 to +0.013 on all five seeds with 58-65% wins; 034). This protocol decides in
advance what five-seed evidence would make R a candidate for the same kind of user decision. It is chosen after seeing one
seed, so its criteria are stricter than 028's.

## Frozen method

Arm R exactly as in 065 (`src/exp065_task1_rest_expert.py --arm R`), cv_seeds 2027, 2028, 2029, 2030, each against the
production reference of 062 on the same seed (`20261009T172902Z_062_production_s2027`, `…173025Z…s2028`, `…173146Z…s2029`,
`…173307Z…s2030`). Seed 2026 is 065's run `20261009T175524Z_065_R`.

## Frozen criteria (all must hold)

1. Δ > 0 on all five seeds.
2. Mean Δ over the five seeds ≥ +0.004.
3. Pooled non-tied folds over the five seeds: ≥ 62% wins.
4. Facebook mean Δ F1 over the five seeds ≥ 0 (the change must not cost facebook).

Outcome if all hold: **candidate for a documented exception** (user decides; a submission would be built and checked, the
ranked file chosen on CV before any score is seen). Otherwise: not adopted, no further variants of this expert.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `3b352bb`, after 065 seed 2026 only |
| 17:56-17:57 | Arm R on 2027-2030 vs the 062 production references | runs `20261009T175634Z_065_R_s2027`, `…175651Z…s2028`, `…175709Z…s2029`, `…175726Z…s2030` |

No deviation from the frozen protocol.

## Results (each seed vs production on the same seed)

| Seed | Run | Δ macro F1 | Wins / losses / ties | rule v2 verdict | facebook Δ F1 |
|---|---|---:|---|---|---:|
| 2026 | `20261009T175524Z_065_R` | +0.0054 | 31 / 17 / 2 | NEAR-MISS | +0.000 |
| 2027 | `20261009T175634Z_065_R_s2027` | +0.0051 | 24 / 20 / 6 | INCONCLUSIVE | −0.002 |
| 2028 | `20261009T175651Z_065_R_s2028` | +0.0067 | 30 / 14 / 6 | NEAR-MISS | +0.007 |
| 2029 | `20261009T175709Z_065_R_s2029` | +0.0097 | 33 / 15 / 2 | NEAR-MISS | +0.011 |
| 2030 | `20261009T175726Z_065_R_s2030` | +0.0059 | 25 / 21 / 4 | INCONCLUSIVE | +0.015 |

| Criterion | Value | Holds |
|---|---|---|
| 1. Δ > 0 on all five seeds | +0.0051 to +0.0097 | ✅ |
| 2. Mean Δ ≥ +0.004 | +0.0066 | ✅ |
| 3. Pooled non-tied wins ≥ 62% | 143 / 230 = 62.2% | ✅ (narrowly) |
| 4. Facebook mean Δ F1 ≥ 0 | +0.006 | ✅ |

## Interpretation

- The rest-of-flow expert gives a small, consistent gain on every seed, comparable to 028 when it was adopted as an
  exception (+0.005 to +0.013 with 58-65% wins). It never passes rule v2 on a single seed.
- Expected effect on the test score: +0.0066 macro F1, about +0.3 Task 1 points, well inside the 81-flow noise (040).
- Criterion 3 holds by a small margin (62.2% vs 62%).

## Decision

Candidate for a documented exception. Adopting it in production, building the submission file into `submissions/` and
uploading need the user's decision. The ranked file is chosen on this CV evidence before any new score is seen.
