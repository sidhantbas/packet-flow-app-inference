---
title: "087: A Meta doorman that does not steal instagram letters (rescues into facebook only)"
created: 2026-10-10
creator: sidhantbas
description: "Frozen protocol and results for a parameter-free change to the 034 Meta gate inside production: flows the gate moves into Meta may become facebook but not instagram."
source:
  - 034_meta_gate.md
  - 083_instagram_google_verifier.md
  - 084_pair_verifiers.md
experiment:
  id: 087
  tasks:
  - task1
  lever: hierarchy
  status: adopted
  verdict: 'The Meta gate may rescue flows into facebook only: BETTER on 3/5 seeds (mean +0.0020, instagram up); later part of 089'
  production: Facebook-only gate rescue (via 089)
---

# 087: A Meta doorman that does not steal instagram letters

**Status: done 2026-10-10. Protocol frozen (`4c2356d`) before any code change or run.**
**Verdict: not adopted; BETTER on 3 of 5 seeds (mean +0.0020; instagram up on every seed, facebook unchanged); test file identical to 88.11.** Results are below.
Do not edit the frozen sections after execution starts. User 2026-10-10: "try the doorman who doesn't steal instagram letters"
(BACKLOG ready idea 2).

## Why

034's Meta gate (the doorman) only moves flows **into** Meta that the two-clerks model put outside it; the whole-run expert then
picks facebook or instagram. It raised facebook F1 (+0.082) but lowered instagram (−0.029): rescued flows that land on instagram
are often other apps (034b: instagram precision 0.81 → 0.74). Facebook was the reason for the gate; instagram has 19 labelled
flows and loses from it.

## Frozen arm

**IG:** production (`models.task1_pair_verifiers`, 084 ALL) with one change in its 034 base: a flow that the 034 model calls
instagram while the two-clerks model (its own `clerks_`) calls it something outside Meta (a gate rescue into instagram) gets
the two-clerks label instead. Gate rescues into facebook, every other rule and both 084 verifiers are unchanged. Nothing is
tuned.

## Decision rule

- cv_seed 2026 vs the Task 1 champion (`20261009T220447Z_084_ALL`) through `runlog`; gate to continue: Δ > 0 and flows fixed
  ≥ 2 × flows broken (majority over repeats, from the report) or, if the report shows no flow-level change, errors removed ≥
  2 × broken over all predictions.
- Then cv_seeds 2027-2030 vs the 084 ALL runs of the same seed. Pass: rule v2 BETTER on all five seeds (a backlog idea
  chosen after many results).
- Pass: build the test file (test features only), official loader, count differences from the 88.11 file. Only a pass whose
  file differs is a submission candidate (one submission left; user approval).

## Boundaries

Train+validation only for model choice; test features only to build files; nothing pretrained; Task 1 only. Production changes
need the user's approval.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-10 | Protocol frozen and committed | before any code change or run |
| 2026-10-10 00:10 | Runner committed (`21e914a`); seed 2026 run twice by accident (a display filter hid the first run's output) | `20261010T001031Z_087_IG`, `20261010T001054Z_087_IG`: all 3,300 predictions identical |
| 2026-10-10 | runlog reproduction check fixed | it compared exact scores with the 6-decimal scores in `index.jsonl` at 1e-12 tolerance, so the second run was wrongly flagged "DIFFER (nondeterminism)"; tolerance now 5e-7 |
| 00:11-00:12 | Seeds 2027-2030 vs the 084 ALL runs of the same seed | `20261010T001140Z_087_IG_s2027`, `…001159Z…_s2028`, `…001218Z…_s2029`, `…001236Z…_s2030` |
| after the runs | Test file built for information (outside the protocol, which builds files only for a pass) | identical Task 1 predictions to the 88.11 file |

## Results (vs production 084 ALL, rule v2)

| Seed | Δ macro F1 | W / L / T | Verdict | instagram | facebook | facebook → instagram (50 folds) |
|---|---:|---|---|---:|---:|---|
| 2026 | +0.0032 | 13 / 1 / 36 | BETTER | +0.023 | 0.000 | 21 → 13 |
| 2027 | +0.0026 | 17 / 3 / 30 | BETTER | +0.024 | 0.000 | 20 → 9 |
| 2028 | −0.0008 | 10 / 7 / 33 | INCONCLUSIVE | +0.001 | 0.000 | |
| 2029 | +0.0007 | 9 / 4 / 37 | NEAR-MISS | +0.012 | 0.000 | 25 → 13 |
| 2030 | +0.0045 | 11 / 1 / 38 | BETTER | +0.029 | 0.000 | 24 → 15 |

Mean Δ +0.0020; 60 wins, 16 losses. Instagram F1 rises on every seed (+0.001 to +0.029) and facebook F1 is unchanged; the
facebook flows no longer sent to instagram go to google or x instead (still wrong), and google/x lose a little.

## Verdict

**Not adopted: BETTER on 3 of 5 seeds; the frozen rule needs 5.** The mechanism works as intended (fewer false instagram calls
on every seed, facebook untouched), but the gain is small and not stable across split sets. Its test file is identical to the
88.11 file, so it could not change the score either way. BACKLOG ready idea 2 is closed.
