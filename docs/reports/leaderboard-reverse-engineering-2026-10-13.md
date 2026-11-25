---
title: "Leaderboard reverse engineering: what the top teams use and what it is worth to us"
created: 2026-10-13
modified: 2026-10-13
creator: sidhantbas
description: "The Final Test Phase leaderboard and the teams' own method notes, read from the platform on 2026-10-13, decoded into ingredients; each ingredient checked against our experiments and our rules; platform facts (submission limits, which upload is ranked) that change our plan."
source:
  - https://competition.aiforgood.itu.int/web/challenges/challenge-page/495/leaderboard
  - experiments/095_disclosed_count_simulation.md
  - experiments/099_class_count_deficit.md
  - experiments/039_capture_order.md
  - experiments/090_stamp_catalogue.md
relation:
  - docs/reports/leaderboard-method-reproduction.md
---

# Leaderboard reverse engineering

> **Superseded in part (2026-10-13).** Section 4 (the ingredient table) is superseded by
> [Leaderboard method reproduction](leaderboard-method-reproduction.md), which now holds the status of every claimed technique
> and the reproduction experiments (102 Infralibre: not reproduced; 103 LLM_ops and 104 RahmaniJ: to run). Sections 1-3, 5 and
> 6 remain the dated snapshot of 13 October: leaderboard, platform facts, team notes, gap and decisions.

Read on 2026-10-13 from the challenge platform (leaderboard, phases and our own submissions pages; nothing was changed). The
method notes are what each team typed; the platform does not check them. We reverse-engineer **methods** from public notes;
we never reverse-engineer test labels from scores (condition 1).

## 1. The leaderboard (Final Test Phase, the 81 test flows, the official ranking)

| Rank | Team | Task 1 macro F1 | Task 2 macro F1 | Total | Shown submission |
|---:|---|---:|---:|---:|---|
| 1 | HeriTech | 0.96 | 0.94 | **94.98** | 2 days ago |
| 2 | Infralibre | 0.94 | 0.94 | 93.74 | 9 days ago |
| 3 | LLM_ops (Lookup-Ensemble v7) | 0.94 | 0.93 | 93.44 | 19 hours ago |
| 4 | RahmaniJ | 0.92 | 0.92 | 92.50 | 31 days ago |
| 5 | Flow State | 0.91 | 0.87 | 88.99 | 1 month ago |
| 6 | 图个乐呵队 (PaFlowInfer-Net-v5) | 0.88 | 0.88 | 88.17 | 22 days ago |
| 7 | Artur Baranovsky (gbdt-v6) | 0.85 | 0.90 | 87.36 | 3 days ago |
| 8 | **Telex (us)** | 0.84 | 0.91 | **87.24** | 3 days ago (upload 7) |

Since 30 September the top moved from 93.19 to 94.98, and Infralibre and LLM_ops are new. **The gap is almost all Task 1**:
the top three are at 0.94-0.96 there, we are at 0.84. In Task 2 they lead us by 0.02-0.035.

## 2. Platform facts that change our plan

| Fact | What we assumed | Consequence |
|---|---|---|
| **Limits: 5 submissions a day, 50 a month, 100 in total** (Phases page) | "7 used, none left" | Uploads are not the constraint; our own rules are |
| **12 Final Test Phase submissions** on the platform: 4 on 30 Sept, 5 on 9 Oct, 2 on 10 Oct, 1 on 12 Oct | 8 in `submissions/uploads.csv` | 4 submissions are not in our records (probably repeated uploads); to reconcile |
| **The leaderboard shows each team's best submission among those ticked "Show on leaderboard"** | Unknown ranking rule | Two of ours are ticked: upload 7 (87.24) and upload 8 (86.36); the board shows 87.24 |
| Deadline 24 Oct 00:59:59 BST | 23 or 24 Oct, timezone unknown | **23 Oct, 23:59:59 UTC** |
| Our method note reads "gg" | — | Organisers read these notes; ours should describe the method and the Task 2 → Task 1 inputs |

With both uploads ticked, the platform picks the better one by test score, which our rule ("decide the ranked entry before the
score, whatever it scores") does not allow. Unticking upload 7 would show 86.36; the rank stays 8th either way (7th is 87.36).
This is the user's decision (section 6).

## 3. What each team says it does

| Team | Note (condensed from the platform) |
|---|---|
| HeriTech (94.98) | "initfix a": nothing usable |
| Infralibre (93.74) | Class-balanced prefix-five ensemble, probability calibration, **disclosed-count analysis**; Task 2 uses only the prefix-five file |
| LLM_ops (93.44) | **Exact first-5-packet signature lookup**, stacked into seed-bagged, Optuna-tuned LightGBM/XGBoost/ExtraTrees/RandomForest (Task 1) and LightGBM ×2 + ExtraTrees + kNN-Manhattan (Task 2); ratio, rate and CV features; post-prefix deltas (Task 1); **packet sizes mod 8 "as SNI-length proxy"** (Task 2); **temporal Gaussian smoothing across same-session neighbours** (σ 0.5 s Task 1, 1.0 s Task 2); prior correction β = 0.25; **Hungarian count matching with the published metadata class counts** |
| RahmaniJ (92.50) | Ensemble on **the first-5-packet features only, the same predictions for both tasks**; **published metadata.json class counts for constrained assignment** |
| Flow State (88.99) | "basic ML" |
| 图个乐呵队 (88.17), Artur Baranovsky (87.36) | No note |
| Telex, us (87.24) | "gg" |

RahmaniJ's and 图个乐呵队's identical Task 1 and Task 2 scores fit one prediction set used for both tasks (same flows, same
labels).

## 4. The ingredients, decoded and priced against our own evidence (superseded)

Kept as written on 13 October. **Correction:** the last row says calibration, prior correction, Optuna tuning, seed bagging,
ratio features and kNN were all tested. Four parts were not: the β = 0.25 prior correction, XGBoost with nested Optuna tuning,
kNN with Manhattan distance, and stacked lookup probabilities. They are queued in experiment 103. Calibration was tested again
in [102](../../experiments/102_flowlens_reproduction.md). Current status: [method reproduction](leaderboard-method-reproduction.md).

| Ingredient | Used by | Our evidence | Status for us | Worth for us |
|---|---|---|---|---|
| **Published test class counts** (constrained or Hungarian assignment) | Infralibre, LLM_ops, RahmaniJ: all three teams that describe their method | Count matching with the true held-out counts was **worse** than production in every arm ([095](../../experiments/095_disclosed_count_simulation.md)); instagram rescue with the oracle count −0.014 ([099](../../experiments/099_class_count_deficit.md)) | ❌ our rule: test `label_counts` are derived from test labels (AGENTS.md, condition 1) | About 0 or negative in CV. It would act exactly where our test predictions deviate most (Task 1 instagram 2 vs about 5, Task 2 x 24 vs about 18), but CV cannot show whether those corrections would be right |
| **Capture-time smoothing** (`start_rel`; flows opened within about a second usually belong to one app session) | LLM_ops | As a feature: +0.003 / +0.013 ([002](../../experiments/002_cv_start_rel.md)); capture order alone 0.50 macro, as a feature −0.040 / −0.015 ([039](../../experiments/039_capture_order.md)). **Smoothing predictions across sub-second neighbours was never measured** | ❌ our decision: capture time and order stay out | **Unknown.** The only ingredient whose size we have not measured |
| **SNI-length proxy** (packet sizes mod 8) | LLM_ops | ClientHello sizes decoded but used only as numbers, no Task 1 gain ([090](../../experiments/090_stamp_catalogue.md)) | ❌ condition 3: no attempt to recover TLS SNI | Not pursued |
| Exact first-5 signature lookup | LLM_ops | Memorisation is right for this data (016); scoped exact-opening override (036) | ✅ allowed | **Already in production** (089 H1, trees with leaf size 1) |
| Prefix-only predictions for both tasks | RahmaniJ | In CV, our full-flow Task 1 model beats prefix-only by +0.10 (0.857 vs 0.754) | ✅ allowed (Task 2 → Task 1) | Negative in CV. Our own uploads point the other way (the Task 2 file scores 0.905 on the same labels, Task 1 0.840), but switching because of that would be **choosing by test score** |
| Calibration, prior correction, Optuna tuning, seed bagging, ratio and rate features, kNN | Infralibre, LLM_ops | Multipliers hurt (004); ratios nothing (008); settings flat (018-020); seed bagging no change (094); kNN member +0.006 near miss (016); thresholds +0.003 (062) | ✅ allowed | ≤ 0.5 points each; tested |
| Leaderboard feedback (many versions: "v5", "v6", "v7", "v8") | Likely, at 5 uploads a day | — | ❌ condition 1 | — |

## 5. What it takes to reach the top three

The top three need +6.2 points over our 87.24; first place +7.7.

- **Within our rules, no measured lever adds more than about 0.5 points** (093, 101).
- **Every described top entry uses at least one ingredient our rules exclude**: the published test counts (all three), capture
  time (one), an SNI-length proxy (one).
- **On this test, opening features carry more than our CV suggests**: prefix-only plus counts reaches 0.92 on both tasks
  (RahmaniJ). Our own Task 2 is 0.905 on the test against 0.754 in CV.
- **Caveats:**
  - The notes are self-reported.
  - With 5 uploads a day on the very test set that ranks the competition, some top scores may partly come from leaderboard
    feedback.
  - The organisers may remove submissions that break the rules. Whether they count published class counts as labels is unknown,
    and we do not contact them.

## 6. Decisions for the user and Charles

| # | Decision | Facts | Options |
|---|---|---|---|
| 1 | **Which upload is ticked "Show on leaderboard"** | Both upload 7 (87.24) and upload 8 (86.36) are ticked; our rule names upload 8 | (a) untick upload 7: the board shows 86.36, rank unchanged (8th), consistent with our rule; (b) leave both: the platform keeps the better by test score |
| 2 | **Measure capture-time smoothing?** | Its size is the one unknown among the leaders' ingredients | Measurement only on train + validation, as 039 did, before any rule decision: frozen protocol, never-used seeds; using it in a submission would still need the user to change the rule |
| 3 | **Published test class counts** | All three described top entries use them; our rule forbids them; CV says no gain for our model | Keep the rule (recommended: no measured gain, real compliance risk) or change it (user decision) |
| 4 | **Reconcile the 12 submissions** | 4 platform submissions are not in `uploads.csv` | Identify them from Sid's upload history; record all 12 |
| 5 | **Method note** | Ours reads "gg" | Write a short, accurate note for the ranked submission (models, Task 2 → Task 1 inputs, exceptions) |
