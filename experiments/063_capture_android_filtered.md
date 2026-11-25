---
title: "063: Android captures and nearest-neighbour-filtered captures in Task 1 training"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: "Frozen protocol and results for two capture uses not tried in 056-058: Android flows recorded on the network side, and only those captured flows whose nearest training flow has the same app label."
source:
  - 056_capture_augmentation.md
  - 058_capture_other_class.md
  - 059_android_signature.md
experiment:
  id: '063'
  tasks:
  - task1
  lever: data
  status: rejected
  verdict: Android captures in training -0.059; same-label-filtered captures -0.010; capture training closed
---

# 063: Android captures and filtered captures in Task 1 training

**Status: done 2026-10-09. Protocol frozen (`32d77cb`) before any code change or run.**
**Verdict: AND WORSE (−0.0587), FILT INCONCLUSIVE (−0.0102). Captured flows (iPhone and Android) have no training use; capture-training tests end here.** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: "can you try to use the captured data, we
need to utilize them". 058 closed the iPhone uses tested so far; this protocol tests two uses not tried before.

## What is new compared with 056-058

1. **Android flows** (059: 62 facebook, 57 instagram; network-side capture whose TCP openings match the dataset, TVD
   0.11) have never been used in training; 056-058 used iPhone flows only.
2. **A same-label filter.** 055 showed most captured Meta flows sit next to training google flows (facebook 2 of 34 had a
   facebook nearest neighbour). Keeping only captured flows whose nearest training flow carries the same label removes
   the flows that pushed google into facebook in 056.

## Frozen arms

Captured rows go into **training folds only**; held-out flows are always original. Model and features: production Task 1
unchanged (`models.task1_meta_gate`, `cv.task1_with_prefix_features`).

| Arm | Captured rows added to each training fold |
|---|---|
| **AND** | all Android facebook (62) and instagram (57) flows, with their session labels |
| **FILT** | from all captured facebook/instagram flows (iPhone 149 from 056 + Android 119), only those whose nearest **original training-fold** flow has the same label |

Filter, computed inside every training fold: the 16 gate-2 columns (`capture_checks.PROX_COLS`), log1p, standardised on
the fold's original rows; Euclidean nearest neighbour among the fold's original rows; keep a captured row if that
neighbour's label equals the captured row's label. Android rows come from
`data/captures/sid-android-20261009T152334Z-check-macshare/` (`--split-merged`, session labels).

## Frozen decision rules

- Each arm vs the Task 1 champion `20261001T173854Z_034_meta_gate` on cv_seed 2026, rule v2.
- Pass only with BETTER on 2026 and on 2027-2030 (production re-run per seed as reference). Confirmation only for arms that
  pass on 2026. Report the number of captured rows kept by the filter.
- A pass is a submission candidate needing the user's approval and a report disclosure (outside data, Task 1 only).
- No arm passes: captured flows (iPhone and Android) have no training use; no further capture-training tests.

## Boundaries

Task 1 only. Original data: train+validation only. Addresses never read here (feature tables only). Production frozen.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `32d77cb`, before any code change or run |
| 2026-10-09 | Runner committed; smoke test on one split | `7b71828`; AND adds 62 facebook + 57 instagram; FILT pool 124 facebook + 144 instagram, keeps 9 + 12 on the test split |
| 17:41 | AND and FILT on cv_seed 2026 | runs `20261009T174106Z_063_AND`, `20261009T174121Z_063_FILT` |

No deviation from the frozen protocol. The rows kept by the filter in each CV fold are not logged (parallel workers); the
smoke-test split kept 21 of 268. No arm passed on 2026, so no confirmation seeds were run.

## Results (vs production Task 1, 0.8277)

| Arm | Macro F1 | Δ | Wins / losses / ties | Verdict |
|---|---:|---:|---|---|
| AND (Android, all) | 0.7690 | −0.0587 | 9 / 41 / 0 | WORSE |
| FILT (same-label filtered, iPhone + Android) | 0.8175 | −0.0102 | 19 / 28 / 3 | INCONCLUSIVE |

| Class | AND Δ F1 | FILT Δ F1 |
|---|---:|---:|
| facebook | −0.295 | −0.067 |
| instagram | −0.056 | −0.016 |
| google | −0.003 | −0.004 |
| mozilla | +0.001 | +0.018 |
| x | −0.013 | −0.000 |
| youtube | +0.015 | +0.007 |

Confusion changes (50 folds summed): AND google → facebook 10 → 75; FILT google → instagram 19 → 34. Both: fewer
instagram → youtube (16 → 4) and fewer mozilla → google (26 → 15 / 18); AND also youtube → google 91 → 63, as in 056.

## Interpretation

- Android flows hurt like iPhone flows (056: −0.084): recorded on the network side they share the dataset's TCP opening
  shapes but not its Meta QUIC sizes (059; their flow lengths were not compared), and they again pull google into facebook.
- The same-label filter removes most of the damage (−0.010 instead of −0.06 to −0.08) but leaves no gain: the few kept
  rows (21 of 268 on the smoke-test split; per-fold counts not logged) still move google flows into instagram and cost facebook −0.067.
- The recurring side effect (fewer non-Meta confusions, mozilla +0.018) appears in every capture arm but always comes with
  a larger Meta loss.

## Decision

Not adopted. By the frozen rule, captured flows (iPhone and Android) have no training use in this project; no further
capture-training tests. Production unchanged (5eb9a8b).
