---
title: "116: Do fingerprint masking or fingerprint-jitter augmentation improve the facebook/instagram decision?"
created: 2026-10-19
creator: sidhantbas
description: "Frozen test of two shortcut-avoidance techniques for the facebook/instagram fingerprint collision found in 115: a pair decider on whole-flow columns only (masking; trees or 1-NN) and pair deciders trained with jittered opening sizes (Task 1 and Task 2), on never-used seeds 2161-2165."
source:
  - 115_identifiability_and_artefacts.md
  - 014_fb_ig_specialist.md
  - 045_facebook_smote.md
  - 100_cross_task_meta_rescue.md
  - 110_task1_rescue_with_109b.md
experiment:
  id: '116'
  tasks: [task1, task2]
  lever: features
  status: rejected
  verdict: 'Neither technique helps: Task 1 masking M −0.0207, masking 1-NN MK −0.0164, jitter J −0.0252, WORSE on 4-5 of 5 seeds each, facebook −0.07 to −0.12; Task 2 jitter J2 −0.0013 (no effect); test changes 0-1'
---

# 116: Fingerprint masking and fingerprint-jitter augmentation

**Status: done 2026-10-19. Protocol frozen (`5662e1b`) before any code or run.**
**Verdict: rejected. Replacing production's facebook/instagram decision with a fingerprint-free or fingerprint-blurred pair
decider loses facebook flows on every seed; jitter in Task 2's specialist changes almost nothing.** Results are below the protocol.
Do not edit the frozen sections after execution starts. Sid, 2026-10-19: "go ahead and run 116" (the two cheap untested techniques
against the fingerprint collision).

## Question and evidence

115: the app signal is mostly the opening packet sizes (a capture-stack fingerprint); facebook and instagram share Meta's, so
on the pair the opening columns add noise: the leave-one-out 1-NN error on the 30 Meta flows is 0.200 on the 17 whole-flow
columns and 0.367 on all 34. Two techniques make the pair decision rely less on the fingerprint:

- **Masking:** decide facebook vs instagram from whole-flow behaviour only.
- **Jitter augmentation:** train the pair decider on copies whose opening sizes are perturbed by a few bytes, so exact sizes such as
  1365 vs 1367 B cannot be used, while coarse size remains.

## Frozen design

**Task 1** (34 production columns). Production (100 FB) is fitted unchanged. For held-out flows that its **089 bundle** calls
facebook or instagram, a pair decider trained only on the facebook + instagram training rows re-decides facebook vs instagram; all
other flows keep production's label (so the 100 rescue, which acts only on flows the bundle calls non-Meta, is untouched).

| Arm | Pair decider |
|---|---|
| P | none: production `models.task1_cross_task` |
| M | unweighted SoftVote on the 17 whole-flow columns (`models.T1_COLS`) |
| MK | 1-nearest neighbour on the 17 whole-flow columns, `log1p` and standardised on the training rows |
| J | unweighted SoftVote on all 34 columns, trained on the original pair rows plus 5 jittered copies each |

**Task 2** (12 production columns).

| Arm | Facebook/instagram specialist |
|---|---|
| P2 | production `models.task2_model` (014: unweighted SoftVote on the pair rows) |
| J2 | the same, trained on the original pair rows plus 5 jittered copies each |

**Jitter** (copies only; seed = model seed): for the opening (Task 1 `p5_` columns; Task 2 all columns), add an independent
uniform integer in [−8, 8] bytes to the upstream and downstream mean packet size of each copy, where that direction has packets
(floored at 0); recompute the bytes as count × mean and the byte ratio as up / max(down, 1) (the decoded formulas, 041). Counts,
spreads, transport and every whole-flow column are unchanged.

- Nothing is tuned; ±8 B and 5 copies are fixed here.
- **Folds:** repeated stratified 5 × 10 on cv_seeds **2161-2165** (0 runs in `results/`; 2156-2160 stay reserved for 112's
  follow-up); model seed = fold index.
- **Smoke check (one fold):** each arm equals P (P2) wherever the bundle (Task 2 base) does not call facebook or instagram; jittered
  copies satisfy bytes = count × mean.
- **Reported:** paired Δ vs P (P2) per seed (rule v2), per-class Δ, flows fixed / broken; test-set effect against every earlier
  uploaded file (no test labels exist or are read).

## Decision rule

An arm counts only if it is rule v2 BETTER than its reference on **all five** seeds. If several Task 1 arms pass, prefer M, then
MK, then J (fewest moving parts). A pass is a production candidate (user decision) and an upload candidate only under the upload
rule (rule v2 on never-used seeds and at least 3 test predictions different from every earlier upload). Otherwise not adopted.

## Boundaries

Task 2 reads only `task2_realtime_prefix5/` files. No decoded first-packet sizes (`s_up_max`) are used. Train + validation labels
only, inside each training fold; test features only for the test-effect check. No upload.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-19 | Protocol frozen and committed | before any code change or run |
| 2026-10-19 | Runner committed (`4afb682`); smoke check (fold 0 of 2161) | every arm equals its reference wherever no Meta call routes the flow (5-6 routed flows of 66); jittered copies satisfy bytes = count × mean |
| 2026-10-19 | All arms on cv_seeds 2161-2165 (`--all`) | 30 runs `…_116_<arm>_s<seed>` |
| 2026-10-19 | `--analyse`, `--test-effect`; `runs.py verify` | `analysis.json`, `test_effect.json`; 821 of 821 runs verified |

No deviation from the frozen protocol.

## Results

Paired Δ against the reference on the same folds ([`116_evidence/analysis.json`](116_evidence/analysis.json),
[`test_effect.json`](116_evidence/test_effect.json)):

| Arm | Seeds 2161 / 2162 / 2163 / 2164 / 2165 | Mean Δ | BETTER | facebook | instagram | Fixed / broken | Test changes |
|---|---|---:|---:|---:|---:|---|---:|
| M (whole-flow trees) | −0.025 W, −0.023 W, −0.024 W, −0.016 W, −0.016 | **−0.0207** | 0 | −0.089 | −0.035 | 22 / 97 | 1 |
| MK (whole-flow 1-NN) | −0.021 W, −0.015 W, −0.016, −0.013 W, −0.016 W | **−0.0164** | 0 | −0.074 | −0.025 | 11 / 69 | 1 |
| J (jittered pair decider, Task 1) | −0.030 W, −0.027 W, −0.025 W, −0.025 W, −0.020 W | **−0.0252** | 0 | −0.116 | −0.035 | 16 / 106 | 0 |
| J2 (jittered Task 2 specialist) | −0.001, +0.002, −0.003, −0.002, −0.002 | −0.0013 | 0 | −0.003 | −0.004 | 10 / 13 | 0 |

(W = rule v2 WORSE.) Test changes are against production 100; each arm also matches at least one earlier upload exactly.

## Verdict

**Rejected.** Both techniques lose in Task 1, clearly and on every seed; in Task 2 jitter has no effect.

1. **Production's facebook/instagram decision already uses more than the fingerprint.** In Task 1 it comes from the whole-run
   expert (17 + 34 columns, all 264 training flows, the keep-facebook rule) inside the Meta gate. A pair decider trained on the
   about 24 facebook/instagram training flows, with or without the fingerprint, decides worse; this repeats 014's finding that a
   pair specialist hurts Task 1 (facebook −0.05 to −0.08).
2. **115's 1-NN advantage on whole-flow columns does not transfer to a decider.** Pooled leave-one-out over 30 flows (error 0.20)
   is a measurement of separability, not a working classifier: inside each fold, 1-NN on 24 flows (MK) still loses facebook flows.
3. **Blurring the exact sizes removes information the pair decider was using** (J: facebook −0.116), so for the trees the 1365 vs
   1367 difference carried some real, if weak, signal.
4. **Task 2's specialist barely depends on exact sizes** (J2 ≈ 0): with only opening columns, there is nothing else for it to use.

The fingerprint collision cannot be engineered around in the facebook/instagram decision with the given columns; 115's research
direction (fingerprint-robust identification, using captures as an out-of-distribution test) stays the open route, beyond this
leaderboard. Production unchanged.
