---
title: "056: Do our own captured Facebook/Instagram flows improve Task 1 in cross-validation?"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for adding captured flows to Task 1 training folds only, judged by rule v2 on the original flows.
source:
  - 055_long_sessions.md
  - 054_independent_extraction_consistency.md
  - 053_tcp_flow_start.md
  - 045_facebook_smote.md
experiment:
  id: '056'
  tasks:
  - task1
  lever: data
  status: rejected
  verdict: 'Captured flows in Task 1 training folds: -0.084 / -0.072; facebook -0.30 to -0.38'
---

# 056: Do our own captured flows improve Task 1 in cross-validation?

**Status: done 2026-10-09. Protocol frozen (`d8bd7b8`) before any code change or run.**
**Verdict: both arms WORSE on cv_seed 2026 (F −0.084, FI −0.072); no confirmation seeds run; not adopted.** Results are below the protocol.
Do not edit the frozen sections after execution starts. Previous steps: [052](052_iphone_pilot.md)-[055](055_long_sessions.md).

## Decision basis

**User decision 2026-10-09 ("yes run the test now"): run this training test although gates 1 and 2 failed (055).**
This overrides, for this test only, the AGENTS.md rule that captures must pass gates 1 and 2 before training use. The
gates were our own pre-check; the cross-validation below is the real test, because it scores only original flows.
Adoption still needs rule v2 on seeds 2026-2030 and the user's approval (production frozen at 5eb9a8b).

## Question

Do captured facebook (and instagram) flows, added to Task 1 training folds only, raise macro F1 on the original
train+validation flows under rule v2?

## Expectation written before the run

About +0.5 Task 1 points expected (+0.01 macro F1), best case +2 to 3 points; about 25% chance of passing rule v2.
Risk: 055 found captured Meta flows nearest to original google flows, so google may lose.

## Frozen data

| Source session | Network | Label | Used in |
|---|---|---|---|
| pilot `02-facebook-feed`, `03-facebook-reels` | Wi-Fi (Facebook QUIC works there, 052) | facebook | F, FI |
| long `02-facebook` | cellular | facebook | F, FI |
| pilot `04-instagram-feed-cellular`, long `03-instagram` | cellular | instagram | FI |

Excluded: YouTube (not a weak class), idle sessions, Wi-Fi Instagram/YouTube (QUIC blocked, 052).
Extraction: `capture_extract.py` default `--tcp-start syn`, plus a new `--split-merged` option that splits merged TCP
frames (> 1514 B) back into MTU-sized frames with the same timestamp (fixes the 053/055 gate 1 failure). Labels: session
app for every flow in the session window. Both Task 1 and Task 2 tables are extracted, so the production features
(Task 1 columns + `p5_` prefix columns, experiment 022) exist for captured flows.

## Frozen method

- Model and features: production Task 1 (`models.task1_meta_gate`, `cv.task1_with_prefix_features`), unchanged.
- Captured rows are appended to every **training fold only** (`cv.evaluate` `resample` hook, as in 045). Held-out
  flows are always original flows. 50 folds (5 × 10), model seed = fold index.
- Arms: **F** (+ captured facebook) and **FI** (+ captured facebook and instagram).
- Reference: Task 1 champion `20261001T173854Z_034_meta_gate` on cv_seed 2026. For confirmation seeds 2027-2030,
  production is re-run on each seed as its reference (no such runs exist yet).

## Frozen decision rules

- An arm passes if rule v2 says BETTER on cv_seed 2026 **and** on 2027, 2028, 2029, 2030 (each against production on
  the same seed). Confirmation seeds run only for an arm that passes on 2026.
- If both arms pass, prefer the one with the larger mean Δ over the five seeds.
- Report per-class Δ (facebook, instagram, google) and flows fixed/broken for every run.
- A pass is a candidate only: adoption needs the user's approval and a report entry (outside data disclosed, Task 1 only).

## Boundaries

Task 1 only (Task 2 never sees captures). Original data: train+validation only. Addresses only in memory during
extraction. Everything runs on this Mac.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `d8bd7b8`, before any code change or run |
| 2026-10-09 | `--split-merged` option + unit test, runner committed | `f936634`; self-test passes |
| 13:20 | `--extract` | 62 facebook flows (merged frames split: 0, 0, 10), 87 instagram flows (46, 58). Gate 1 now **PASS**; gate 2 FAIL. Evidence `data/captures/056-augmentation/` |
| 13:21:22-13:21:36 | Arm F, cv_seed 2026 | run `20261009T132136Z_056_aug_F` |
| 13:21:37-13:21:53 | Arm FI, cv_seed 2026 | run `20261009T132153Z_056_aug_FI` |

Both runs carry a `dirty-tree` warning: the source was committed (`f936634`), but the new run folders, the evidence
folder and unrelated local files were not yet committed; runlog records the code hashes. Per the frozen rule, no
confirmation seeds were run because neither arm passed on 2026.

## Results

| Run | Macro F1 | Δ vs production (0.8277) | Wins / losses (50 folds) | Verdict |
|---|---:|---:|---|---|
| F (+62 facebook) | 0.7438 | **−0.0839** | 2 / 48 | WORSE |
| FI (+62 facebook, +87 instagram) | 0.7560 | **−0.0717** | 6 / 44 | WORSE |

| Class | F Δ F1 | FI Δ F1 |
|---|---:|---:|
| facebook | −0.377 | −0.298 |
| instagram | −0.086 | −0.101 |
| google | −0.010 | +0.002 |
| mozilla | −0.014 | −0.013 |
| x | −0.024 | −0.021 |
| youtube | +0.007 | +0.001 |

Main confusion changes (all 50 folds summed), arm F: google → facebook 10 → 96, x → facebook 1 → 42,
youtube → facebook 2 → 31, mozilla → facebook 0 → 29, instagram → facebook 26 → 53. Arm FI also: google → instagram
19 → 45, facebook → instagram 22 → 47. Side effect: fewer google ↔ youtube errors (youtube → google 91 → 68).

## Interpretation

- The risk named before the run happened: captured flows labelled facebook sit where the training data has google, x,
  youtube and mozilla flows (055 nearest labels), so the model learns to call those facebook. Facebook precision collapses.
- The expected value written before the run (+0.01 macro F1) was wrong in sign; the actual effect is about −4 Task 1 points.
- Session labels add some background flows, but with 96-99% of packets from the app (052), mislabelling is unlikely to
  explain a loss this large. The captured flows simply do not look like the organisers' facebook flows.

## Decision

Not adopted. Production unchanged (5eb9a8b). Captured flows from this iPhone are not used for training in this form.

## Restart point and next

- Any further capture use would need a capture that resembles the organisers' flows (matching phone/OS/app versions, 055),
  not more data from this iPhone. Do not repeat this test with more iPhone sessions.
- Weighting the captured rows down (not in this protocol) would most likely only reduce the damage; turning
  −0.08 into a rule-v2 pass is unlikely. Not planned (not tested).
