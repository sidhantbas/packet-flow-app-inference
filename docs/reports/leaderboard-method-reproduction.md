---
title: "Leaderboard method reproduction: four top-entry claims tested as experiments 102-105, follow-ups 106-108"
created: 2026-10-13
modified: 2026-10-13
creator: sidhantbas
contributor: charles-cai
description: "The method notes of the leaderboard entries that describe a method, verbatim, in our experiments table format, and the detailed record of their reproduction on our data (experiments 102-105) and of the follow-ups on the levers they may not disclose (106-108): every leaderboard and cross-validation score, design, per-seed results, ingredients, test-set effect, due diligence, synthesis and reproducibility. The claims are self-reported and unverified."
source:
  - submissions/raw/leaderboard-final-test-2026-10-13.txt
  - submissions/raw/leaderboard-final-test-2026-10-13-evening.txt
  - submissions/raw/upload-07-score.txt
  - submissions/raw/upload-08-score.txt
  - docs/reports/tested-methods-and-leaderboard.md
  - docs/reports/leaders-vs-ours-dedup.md
---

# Leaderboard method reproduction

## 1. Summary table

One experiment per leaderboard method note (102-104 from the 13 October morning snapshot; 105 from the evening snapshot, [`submissions/raw/leaderboard-final-test-2026-10-13-evening.txt`](../../submissions/raw/leaderboard-final-test-2026-10-13-evening.txt)). **Technique** and **Scores** are copied verbatim
from the leaderboard ([`submissions/raw/leaderboard-final-test-2026-10-13.txt`](../../submissions/raw/leaderboard-final-test-2026-10-13.txt),
read 2026-10-13); the method name is in bold. **Insight** says what earlier experiments already cover. **Kept**: ✓ promoted,
✗ aborted, ⏳ not yet run. The notes are self-reported, so reproducing a method tests whether it helps our model, not whether it
explains their score.

| # | Technique | Scores | Insight | Kept |
|---|---|---|---|:---:|
| 102 | **FlowLens-v8-Mozilla** (Infralibre): Class-balanced prefix-five ensemble with probability calibration and disclosed-count analysis. Task 2 uses only the released realtime prefix-five features; Task 1 remains unchanged. | Task 1 Macro F1 0.94, Task 1 Accuracy 0.93, Task 1 Score 46.94, Task 2 Macro F1 0.94, Task 2 Accuracy 0.91, Task 2 Score 46.79, Total 93.74 | Partly done: [095](../../experiments/095_disclosed_count_simulation.md) simulated it (calibrated balanced ensemble + count matching), worse than production in every arm. The prefix-five ensemble is our Task 2 production model (014). Disclosed counts come from test labels: CV measurement only. **Reproduced in [102](../../experiments/102_flowlens_reproduction.md): not reproduced.** The claim as written is WORSE than production on all 5 never-used seeds (Task 2 −0.036); disclosure adds −0.005 over training-share counts. On our test file the recipe would move 6-7 Task 2 predictions off our x surplus: consistent with their 0.94, not supported by CV | ✗ |
| 103 | **Lookup-Ensemble-v7** (LLM_ops): Task-specific exact-signature lookup (first-5-packet fingerprint) blended with a seed-bagged ensemble of Optuna-tuned LightGBM, XGBoost, ExtraTrees, and RandomForest (Task 1) / LightGBM×2 + ExtraTrees + KNN-Manhattan (Task 2). Features: raw header statistics + ratio/rate/CV features; Task 1 adds post-prefix delta features; Task 2 adds mod-8 byte features as SNI-length proxy. Stacked lookup probabilities feed the tree ensemble. Temporal Gaussian smoothing (σ=0.5 s for T1, 1.0 s for T2) blends flow predictions across same-session neighbours. Mild prior correction (β=0.25) guards macro-F1 on rare classes. Hungarian count-matching uses published metadata class counts for both tasks. No IPs, DNS, SNI, payload, or test labels used. | Task 1 Macro F1 0.94, Task 1 Accuracy 0.93, Task 1 Score 46.94, Task 2 Macro F1 0.93, Task 2 Accuracy 0.91, Task 2 Score 46.50, Total 93.44 | Partly done: exact lookup (036) and post-prefix deltas (030, 065) are in production; seed bagging (094), ratio features (008) and count matching (095) gave no gain. Not yet tried: stacked lookup probabilities, XGBoost, Optuna, kNN-Manhattan, β = 0.25, temporal smoothing. Out of bounds: mod-8 SNI-length proxy (condition 3); counts and capture time are CV measurement only. **Reproduced in [103](../../experiments/103_lookup_ensemble_reproduction.md): not reproduced.** The claim (minus the SNI proxy) is WORSE than production on all 5 never-used seeds in both tasks (−0.065 each); their base starts 0.07-0.10 lower; capture-time smoothing hurts (−0.021 / −0.016); prior correction β = 0.25 helps Task 1 alone (+0.006) | ✗ |
| 104 | **Early-Flow Ensemble** (RahmaniJ): Ensemble classifier using only the released first-5-packet features for early application inference. The same early-flow predictions are used for both tasks. Published metadata.json class counts are used for constrained assignment. No private labels, external datasets, DNS, SNI, IP addresses, URLs, domains, payloads, or prohibited features are used. | Task 1 Macro F1 0.92, Task 1 Accuracy 0.90, Task 1 Score 46.25, Task 2 Macro F1 0.92, Task 2 Accuracy 0.90, Task 2 Score 46.25, Total 92.50 | Partly done: first-5-packet features alone score 0.754 in our CV (014) against 0.857 for our full-flow Task 1 model; count-constrained assignment was worse in [095](../../experiments/095_disclosed_count_simulation.md). Counts: CV measurement only. **Reproduced in [104](../../experiments/104_early_flow_reproduction.md): not reproduced.** WORSE than production on all 5 never-used seeds (Task 1 −0.148, Task 2 −0.064); one prediction set does serve both tasks (identical fold scores); published counts add +0.001 over training shares. Without timing it reproduces our own Task 2 test file exactly | ✗ |
| 105 | **FlowLens-v9-PairSwap** (Infralibre, new leader, read 2026-10-13 evening): Class-balanced cross-view ensemble with a count-preserving Task 1 consensus swap. Task 2 remains the validated prefix-five-only model with no Task 1 information used. | Task 1 Macro F1 0.96, Task 1 Accuracy 0.95, Task 1 Score 48.21, Task 2 Macro F1 0.94, Task 2 Accuracy 0.91, Task 2 Score 46.79, Total 95.01 | Successor of 102 (v8 → v9): only Task 1 changed, +1.27 points (Task 1 F1 about 0.939 → 0.964, roughly one or two more correct flows of 81); Task 2 identical. "Cross-view" = full-flow and first-5 views together, which our Task 1 production already does (022, 028, 089). "Count-preserving swap" = exchanging labels between pairs of flows so the predicted class counts stay fixed, presumably at the published test counts (excluded by our rule; count methods gave no CV gain in 095, 099, 102-104). A one- or two-flow change cannot be told apart from leaderboard feedback. **Reproduced in [105](../../experiments/105_pairswap_reproduction.md), with due diligence: not reproduced.** WORSE than production on all 5 never-used seeds (−0.070); a label-blind swap breaks 2-3 correct flows per fixed one; their +2 correct flows at constant counts came out of a blind swap in only 1-2% of batches; on our test set the swap changes nothing | ✗ |

HeriTech ("initfix a"), Flow State ("basic ML"), 图个乐呵队 and Artur Baranovsky (no note) describe no method to reproduce.

**In one line:** none of the four claims beats our production in cross-validation on never-used seeds; every one starts from a
weaker base model, and none of the extras they describe closes the gap on our data. The follow-ups on what they may not
disclose (106-108) add nothing either; section 1a has every score.

## 1a. All scores in one place

**Leaderboard, Final Test Phase, 13 October evening** (copied from
[`submissions/raw/leaderboard-final-test-2026-10-13-evening.txt`](../../submissions/raw/leaderboard-final-test-2026-10-13-evening.txt);
the platform rounds F1 and accuracy to two decimals). Morning totals from the morning snapshot.

| Rank | Team (method name) | Task 1 F1 | Task 1 Acc. | Task 1 Score | Task 2 F1 | Task 2 Acc. | Task 2 Score | Total | Morning total |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Infralibre (FlowLens-v9-PairSwap) | 0.96 | 0.95 | 48.21 | 0.94 | 0.91 | 46.79 | **95.01** | 93.74 (v8) |
| 2 | HeriTech | 0.96 | 0.95 | 47.83 | 0.94 | 0.93 | 47.14 | **94.98** | 94.98 |
| 3 | LLM_ops (Lookup-Ensemble v7) | 0.94 | 0.93 | 46.94 | 0.93 | 0.91 | 46.50 | **93.44** | 93.44 |
| 4 | RahmaniJ | 0.92 | 0.90 | 46.25 | 0.92 | 0.90 | 46.25 | **92.50** | 92.50 |
| 5 | Flow State | 0.91 | 0.91 | 45.61 | 0.87 | 0.90 | 43.37 | **88.99** | 88.99 |
| 6 | 图个乐呵队 (PaFlowInfer-Net-v5) | 0.88 | 0.85 | 44.08 | 0.88 | 0.85 | 44.08 | **88.17** | 88.17 |
| 7 | Artur Baranovsky (gbdt-v6) | 0.85 | 0.88 | 42.49 | 0.90 | 0.88 | 44.87 | **87.36** | 87.36 |
| 8 | Telex (us) | 0.84 | 0.89 | 41.99 | 0.91 | 0.89 | 45.25 | **87.24** | 87.24 |

**Our uploads, exact scores** (platform JSON in `submissions/raw/`):

| Upload | Model | Task 1 F1 | Task 1 Score | Task 2 F1 | Task 2 Score | Total |
|---|---|---:|---:|---:|---:|---:|
| 6 | 084 Task 1 + 014 Task 2 (best ever) | — | — | — | — | 88.11 |
| 7 | 089 Task 1 + 014 Task 2 (displayed) | 0.8397 | 41.99 | 0.9051 | 45.25 | 87.24 |
| 8 | 100 Task 1 + 014 Task 2 (ranked entry by our rule) | 0.8222 | 41.11 | 0.9051 | 45.25 | 86.36 |

**Gap to first place:** 95.01 − 87.24 = 7.77 points: Task 1 6.22 (about 5 flows of 81), Task 2 1.54 (about 2 flows).

**Every reproduction and follow-up, cross-validation** (macro F1, mean of five never-used seeds; production = P on the same
folds; test changes = our submitted test predictions that the arm would change, no labels involved):

| # | What was tested | Task 1: P → arm (Δ) | Task 2: P → arm (Δ) | Seeds BETTER (of 5) | Test changes | Kept |
|---|---|---|---|---:|---|:---:|
| 102 | Infralibre v8 (93.74): balanced first-5 ensemble + sigmoid calibration + disclosed counts | not claimed | 0.759 → 0.723 (−0.036) | 0 | 6-7 (count arms, training shares) | ✗ |
| 103 | LLM_ops (93.44): lookup + tuned bagged ensemble + prior β + capture-time smoothing + disclosed counts | 0.849 → 0.784 (−0.065) | 0.766 → 0.701 (−0.065) | 0 | 8 / 4 (compliant L3) | ✗ |
| 104 | RahmaniJ (92.50): first-5 only, one prediction set for both tasks + disclosed counts | 0.849 → 0.701 (−0.148) | 0.765 → 0.701 (−0.064) | 0 | 14 / 11 (E1S) | ✗ |
| 105 | Infralibre v9 (95.01): cross-view ensemble + count-preserving consensus swap | 0.850 → 0.780 (−0.070) | not claimed | 0 | 4 (V1); 0 (swap on production) | ✗ |
| 106 | Prior correction β = 0.25 inside our Task 1 production | 0.849 → 0.850 (+0.001) | — | 1 | 1 | ✗ |
| 107 | Same-moment flow labels, σ = 0.5 s (measurement only; best arm) | 0.852 → 0.796 (−0.056) | 0.762 → 0.716 (−0.046, σ = 1 s) | 0 | not built | ✗ |
| 108 | Exact-opening lookup on our Task 2 production | — | 0.766 → 0.766 (+0.0003) | 0 | 0 | ✗ |

## 2. How each claim was reproduced

The same procedure for all four, so the results are comparable and every number can be re-run.

```mermaid
flowchart LR
  N["📋 Method note<br/>copied verbatim"]:::entry --> R["🔍 Reading table<br/>unknowns fixed<br/>before any run"]:::process
  R --> F["📝 Frozen protocol<br/>committed first"]:::storage
  F --> C["🧩 Arms built from<br/>src/flowkit"]:::process
  C --> V["🔁 5 × 10 CV on<br/>5 never-used seeds<br/>paired with production"]:::process
  V --> D{"⚖️ Rule v2<br/>on all 5 seeds"}:::decision
  D --> T["🧪 Test-set effect<br/>no labels"]:::process
  T --> W["✅ Log, evidence,<br/>this report"]:::output
  classDef entry fill:#1e1b4b,color:#c7d2fe,stroke:#4338ca,stroke-width:2px
  classDef process fill:#0c4a6e,color:#bae6fd,stroke:#0284c7
  classDef storage fill:#14532d,color:#bbf7d0,stroke:#16a34a
  classDef decision fill:#431407,color:#fed7aa,stroke:#ea580c
  classDef output fill:#064e3b,color:#6ee7b7,stroke:#10b981
```

| Step | What it means |
|---|---|
| Verbatim claim | The note is copied unchanged from the saved leaderboard page; the protocol quotes it |
| Reading table | Each phrase gets one implementation; anything the note leaves open (members, folds, weights, constants) is fixed in the protocol before any code, so we cannot tune towards a result |
| Ingredient ladder | Arms add one ingredient at a time, so each ingredient's effect is a paired difference on the same folds |
| Never-used seeds | 102: 2101-2105; 103: 2106-2110; 104: 2111-2115; 105: 2116-2120; 106: 2121-2125; 107: 2126-2130; 108: 2131-2135. None had any run before |
| Paired with production | Every arm runs against production on identical folds; verdicts use rule v2 (Δ > 0, ≥ 70% of non-tied folds won, ≥ 10 non-tied), required on all five seeds |
| Excluded ingredients | Published test counts and capture time are excluded from our submissions by our rules. They are **measured** in cross-validation only: "disclosed" counts are the held-out fold's own labels. The SNI-length proxy is not built at all (condition 3) |
| Test-set effect | Arms usable in a submission are fitted on train + validation and applied to the 81 test flows; we count the predictions they would change. No labels are involved, and nothing is uploaded |
| Due diligence (105) | The claim's arithmetic and a label-blind version of the method are checked against the size of the score change it would have to explain |

## 3. Experiment 102: FlowLens-v8-Mozilla (Infralibre, 93.74)

**Claim:** "Class-balanced prefix-five ensemble with probability calibration and disclosed-count analysis. Task 2 uses only the
released realtime prefix-five features; Task 1 remains unchanged." Task 2 only; their Task 1 method is not described.
[Log](../../experiments/102_flowlens_reproduction.md) · [evidence](../../experiments/102_evidence/) · `src/exp102_flowlens_reproduction.py`

| Arm | Built as | Task 2 macro F1 (mean of 5 seeds) | Δ vs production |
|---|---|---:|---:|
| P | Production Task 2 (014) | 0.759 | — |
| F0 | Balanced SoftVote on the 12 opening columns | 0.740 | −0.019 |
| F1S / F1I | + sigmoid / isotonic calibration on cross-validated probabilities | 0.737 / 0.744 | −0.022 / −0.015 |
| **F2S-D** | **+ sigmoid + disclosed counts (the claim)** | **0.723** | **−0.036** |
| F2I-D | + isotonic + disclosed counts | 0.733 | −0.026 |
| F2S-S / F2I-S | + calibration + training-share counts (compliant) | 0.728 / 0.739 | −0.031 / −0.021 |

Claim arm per seed (Δ, folds won / lost): 2101 −0.033 (9/41) · 2102 −0.038 (9/41) · 2103 −0.047 (9/41) · 2104 −0.030 (8/42) ·
2105 −0.034 (9/41).

| Ingredient | Δ |
|---|---:|
| Their base instead of production (it lacks our facebook/instagram stage) | −0.019 |
| Sigmoid / isotonic calibration | −0.003 / +0.004 |
| Disclosed counts after calibration | −0.014 / −0.012 |
| Disclosed counts instead of training-share counts | −0.005 |

**Test-set effect:** calibration changes none of our 81 Task 2 test predictions. Count assignment with training shares changes 6
(sigmoid) or 7 (isotonic), every one away from x, which our file over-predicts (24 against about 18 expected): 3 to mozilla, the
rest to facebook, instagram, youtube and google.
**Verdict:** not reproduced. Their Task 2 0.94 is *consistent* with the count step if 2-3 of those moves are right on this test
set, but cross-validation says such moves are wrong more often than right.

## 4. Experiment 103: Lookup-Ensemble-v7 (LLM_ops, 93.44)

**Claim:** exact first-5-packet lookup stacked into a seed-bagged, Optuna-tuned ensemble (LightGBM, XGBoost, ExtraTrees,
RandomForest for Task 1; LightGBM ×2, ExtraTrees, kNN-Manhattan for Task 2), ratio/rate/CV features, post-prefix deltas
(Task 1), an SNI-length proxy (Task 2, not built), temporal smoothing over capture time, prior correction β = 0.25, and Hungarian
matching to the published counts. Both tasks.
[Log](../../experiments/103_lookup_ensemble_reproduction.md) · [evidence](../../experiments/103_evidence/) · `src/exp103_lookup_ensemble_reproduction.py`

| Arm | Adds | Task 1 | Δ | Task 2 | Δ |
|---|---|---:|---:|---:|---:|
| P | Production | 0.849 | — | 0.766 | — |
| L0 | Their base ensemble and features | 0.774 | −0.074 | 0.667 | −0.099 |
| L1 | + stacked and blended lookup | 0.770 | −0.079 | 0.724 | −0.042 |
| L2 | + Optuna (15 trials, nested 3-fold) + 3-seed bagging | 0.774 | −0.075 | 0.729 | −0.037 |
| L3 | + prior correction β = 0.25 (compliant end) | 0.780 | −0.068 | 0.723 | −0.043 |
| L4 | + temporal smoothing (measured only) | 0.760 | −0.089 | 0.706 | −0.060 |
| **L5** | **+ disclosed counts (the claim, minus the SNI proxy)** | **0.784** | **−0.065** | **0.701** | **−0.065** |

Claim arm per seed, Task 1 (Δ, won / lost): 2106 −0.065 (11/39) · 2107 −0.057 (9/41) · 2108 −0.053 (10/40) · 2109 −0.078 (7/43) ·
2110 −0.072 (10/40). Task 2: −0.074 (7/43) · −0.060 (9/41) · −0.063 (5/45) · −0.058 (4/46) · −0.071 (5/45).

| Ingredient | Task 1 | Task 2 |
|---|---:|---:|
| Their base instead of production | −0.074 | −0.099 |
| Lookup, stacked and blended | −0.005 | **+0.057** |
| Optuna tuning and bagging | +0.004 | +0.004 |
| Prior correction β = 0.25 | **+0.006** (better on all 5 seeds) | −0.006 |
| Temporal smoothing over capture time | **−0.021** | **−0.016** |
| Disclosed counts | +0.024 | −0.006 |

**Test-set effect:** the compliant arms change 8-11 Task 1 and 3-7 Task 2 test predictions; L3 cuts our facebook calls from 4 to
1. **Verdict:** not reproduced. The gap is their base; the lookup's Task 2 gain is what our production already gets from
memorising openings; capture-time smoothing hurts both tasks. One lead: β = 0.25 on Task 1 (BACKLOG).

## 5. Experiment 104: Early-Flow Ensemble (RahmaniJ, 92.50)

**Claim:** "Ensemble classifier using only the released first-5-packet features ... The same early-flow predictions are used for
both tasks. Published metadata.json class counts are used for constrained assignment."
[Log](../../experiments/104_early_flow_reproduction.md) · [evidence](../../experiments/104_evidence/) · `src/exp104_early_flow_reproduction.py`

| Arm | Built as | Task 1 | Δ | Task 2 | Δ |
|---|---|---:|---:|---:|---:|
| P | Production | 0.849 | — | 0.765 | — |
| E0 | Balanced SoftVote, 17 first-5 columns | 0.699 | −0.150 | 0.699 | −0.065 |
| E0N | Same, 12 columns without timing | 0.746 | −0.103 | 0.746 | −0.019 |
| **E1** | **E0 + disclosed counts (the claim)** | **0.701** | **−0.148** | **0.701** | **−0.064** |
| E1S | E0 + training-share counts (compliant) | 0.700 | −0.149 | 0.700 | −0.064 |

Claim arm per seed, Task 1: −0.157 (1/49) · −0.150 (1/49) · −0.127 (3/47) · −0.143 (5/45) · −0.163 (0/50). Task 2: −0.058 (8/42) ·
−0.076 (5/45) · −0.057 (8/42) · −0.063 (9/41) · −0.064 (6/44).

| Ingredient | Δ (identical in both tasks) |
|---|---:|
| Timing columns in the opening | −0.046 |
| Disclosed counts | +0.002 |
| Training-share counts | +0.001 |
| Disclosure itself | +0.001 |

**Structure verified:** every arm scores identically in Task 1 and Task 2 on every fold, because the two tasks share flows and
labels; one prediction set does serve both. **Test-set effect:** without timing, their method reproduces our own Task 2 test file
exactly (0 changes). That file scored 0.905 on the shared test labels, so a prefix-only prediction set also scores about 0.905 on
Task 1's test, above our Task 1's 0.840, although cross-validation ranks our full-flow model 0.10 higher. Their extra 0.015 would
come from counts, which move 11 of our Task 2 test predictions. **Verdict:** not reproduced; acting on it would mean choosing by
test score.

## 6. Experiment 105: FlowLens-v9-PairSwap (Infralibre, 95.01), with due diligence

**Claim:** "Class-balanced cross-view ensemble with a count-preserving Task 1 consensus swap. Task 2 remains the validated
prefix-five-only model with no Task 1 information used." Only Task 1 changed from v8: 46.94 → 48.21 points.
[Log](../../experiments/105_pairswap_reproduction.md) · [evidence](../../experiments/105_evidence/) · `src/exp105_pairswap_reproduction.py`

| Arm | Built as | Task 1 macro F1 | Δ vs production |
|---|---|---:|---:|
| P | Production | 0.850 | — |
| V0 | Cross-view ensemble (17 Task 1 + 12 opening columns) | 0.785 | −0.065 |
| **V1** | **V0 + consensus pair swap (the claim)** | **0.780** | **−0.070** |
| V2 | Production + the swap against our Task 2 view | 0.830 | −0.020 |
| V3 | V0 matched to true counts, then swapped (measured only) | 0.793 | −0.056 |

Claim arm per seed: −0.069 (9/41) · −0.068 (8/41) · −0.067 (9/41) · −0.061 (10/40) · −0.086 (4/45).

**Due diligence:**

| Check | Finding |
|---|---|
| D1 What their score change means | Task 1 accuracy 0.93 → 0.95 = 75 → 77 correct of 81: exactly +2 flows, which is what one perfect pair swap gives at constant class counts |
| D2 What a label-blind swap does (250 folds) | Fixed / broken flows: 44 / 142 (V0 → V1), 70 / 236 (P → V2), 54 / 99 (V3M → V3): **2-3 correct flows broken per fixed one** |
| D3 How often a blind swap gives their outcome | Net +2 or more with nothing broken in **3, 3 and 5 of 250 folds (1-2%)** |
| D4 The cross-view ensemble alone | 0.065 below production, which already combines whole-flow, opening and rest-of-flow views |
| D5 The Task 2 sentence | A compliance statement (condition 2); Task 2 unchanged since v8 |

**Reading:** the note does not describe a mechanism that produces +2 reliably. The jump is more consistent with a lucky draw, or
with a pair chosen by leaderboard feedback (5 uploads a day on the set that ranks the competition). This is a finding about the
note, not an accusation, and we never act on it. On our own test predictions the swap changes nothing.

## 7. Experiment 106: prior correction inside our production

**Question:** the one lead 103 left open. Prior correction β = 0.25 lifted LLM_ops's own Task 1 ladder on every seed (+0.006);
does it lift ours? It is allowed in a submission.
[Log](../../experiments/106_prior_correction_production.md) · [evidence](../../experiments/106_evidence/) · `src/exp106_prior_correction_production.py`

| Arm | Built as | Task 1 macro F1 (mean of 5 seeds) | Δ vs production |
|---|---|---:|---:|
| P | Production `task1_cross_task` (100) | 0.849 | — |
| **B25** | **P with the experts' averaged probabilities prior-corrected before the Meta gate,** $p_c \propto p_c / \pi_c^{0.25}$ | **0.850** | **+0.0010** |

Per seed (Δ, wins/losses): +0.0022 (20/13) · +0.0004 (18/18) · −0.0010 (14/19) · +0.0043 (23/9) · −0.0008 (15/17). Verdicts: NEAR-MISS, INCONCLUSIVE, INCONCLUSIVE, BETTER, INCONCLUSIVE.

**What it changes:** 247 held-out predictions over five seeds, 117 fixed and 89 broken, mostly moves out of google (to
youtube and mozilla), some x → mozilla. **Test-set effect:** 1 prediction (`flow_000906` google → youtube), below the upload rule's 3.
**Verdict:** not adopted. Our production already corrects for rarity where it matters (Meta gate, verifiers, rescues), so the
prior adds little on top.

## 8. Experiment 107: labels of flows opened at the same moment (measurement only)

**Question:** the most plausible lever a leader might not disclose. 43% of labelled flows start within 1 s of the previous one,
so a flow could copy the label of labelled flows opened at the same moment. Capture time is excluded from our submissions; this
measures what the lever is worth. Both tasks.
[Log](../../experiments/107_temporal_label_neighbours.md) · [evidence](../../experiments/107_evidence/) · `src/exp107_temporal_label_neighbours.py`

Task 1 (production `task1_cross_task`):

| Arm | Task 1 macro F1 | Δ vs P | Flows fixed / broken |
|---|---:|---:|---|
| P | 0.852 | — | — |
| N05: override where neighbours within σ = 0.5 s agree (W ≥ 0.5, share ≥ 0.8) | 0.796 | −0.056 | 318 / 988 |
| N10: same, σ = 1 s | 0.776 | −0.077 | 398 / 1222 |
| N20: same, σ = 2 s | 0.761 | −0.0915 | 292 / 1314 |
| NN: label of the nearest training flow in time, no model | 0.502 | −0.351 | 770 / 5588 |

Task 2 (production `task2_model`):

| Arm | Task 2 macro F1 | Δ vs P | Flows fixed / broken |
|---|---:|---:|---|
| P | 0.762 | — | — |
| N05 (σ = 0.5 s) | 0.703 | −0.058 | 446 / 953 |
| N10 (σ = 1 s) | 0.716 | −0.046 | 605 / 1121 |
| N20 (σ = 2 s) | 0.702 | −0.060 | 451 / 1074 |
| NN (nearest flow in time) | 0.502 | −0.260 | 1071 / 5119 |

Every arm is WORSE on every seed in both tasks (Task 1 N05 per seed: −0.0548 (8/40) · −0.0591 (6/44) · −0.0639 (8/42) · −0.0529 (8/42) · −0.0501 (7/43)).
**Why:** labels follow the destination server, not the app on screen (041); an app in use opens connections to several services
at once, so flows opened together often carry different labels. **Verdict:** no such lever; capture time does not explain the
leaderboard, as smoothing (103) or as label copying (here).

## 9. Experiment 108: exact-opening lookup on our Task 2 production

**Question:** the one leader technique tested only on a leader's base. 103's exact first-5 lookup added +0.057 on Task 2 over
LLM_ops's base; Task 1 production already has it (036), Task 2 production had never been tried.
[Log](../../experiments/108_task2_exact_opening_override.md) · [evidence](../../experiments/108_evidence/) · `src/exp108_task2_exact_opening_override.py`

| Arm | Built as | Task 2 macro F1 (mean of 5 seeds) | Δ vs production |
|---|---|---:|---:|
| P | Production `task2_model` (014) | 0.766 | — |
| H | P; an exact 12-column opening seen in training with one label takes that label, Meta excluded (036's rule) | 0.766 | +0.0003 |
| HA | Same, Meta included (closest to the leader's lookup) | 0.766 | +0.0003 |

Per seed (Δ, wins/losses): +0.0004 (2/0) · +0.0000 (0/0) · +0.0000 (0/0) · +0.0005 (2/0) · +0.0005 (2/0); INCONCLUSIVE on all five (at most 2 non-tied folds). H and HA are
identical. **What it changes:** 6 of 1650 held-out predictions, all mozilla → google, all right. **Test-set effect:** 0.
**Verdict:** no gain: production's trees already memorise exact openings; Task 2's remaining errors sit on openings seen with
more than one label (093), which no lookup can resolve.

## 10. Synthesis across 102-108

| Lesson | Evidence |
|---|---|
| **The leaders' base models are weaker than ours in cross-validation** | Their bases start 0.019-0.150 below production (102 F0, 103 L0, 104 E0, 105 V0) |
| **Published test counts never help our models** | Disclosed vs training-share counts: −0.005 (102), +0.001 (104); counts alone: −0.014 to +0.024; and 095, 099 before |
| **Capture time does not explain their scores** | Smoothing predictions −0.021 / −0.016 (103); copying neighbours' labels −0.056 to −0.092 / −0.046 to −0.060 (107) |
| **What genuinely helps is already in production** | Exact-opening memory (036, and Task 2's trees: 108), post-prefix features (089), cross-view combination (022, 028) |
| **The one transferable ingredient adds almost nothing to us** | Prior correction: +0.006 on their base (103), +0.001 on ours (106) |
| **Structural claims check out, performance claims do not** | One prediction set for both tasks is exactly true (104); the methods' scores are not reproduced |
| **On this test set, opening features and counts may be lucky** | Our Task 2 test (0.905) is far above its CV (0.76); count steps move our x surplus; 105's +2 is a 1-2% event for its own rule |
| **Leaderboard notes are claims, not methods** | Self-reported, sometimes strategic, and a few flows decide a score on 81 test flows |

No open lead is left: every technique in the notes is in production, measured as no gain, or excluded by the rules (the full
deduplication is in [Leaders against ours](leaders-vs-ours-dedup.md)). Nothing here justifies an upload under the upload rule.
Production stays; the next step is the technical report.

## 11. Reproducibility and data management

| Item | Value |
|---|---|
| Runs | 265 CV runs: 102 40, 103 70, 104 50, 105 30, 106 10, 107 50, 108 15; all verify with `src/runs.py verify` |
| Run folders | `results/<UTC stamp>_<NNN>_<arm>_s<seed>/` (103, 104, 107: `<T1|T2>_<arm>`), each with predictions, fold scores, config and hashes |
| Evidence | `experiments/<NNN>_evidence/analysis.json` (per-seed paired results) and `test_effect.json` (test predictions changed; none for 107) |
| Protocols | Frozen and committed before any code: `30c54d6` (102), `f664196` (103), `0df473f` (104), `f5975e2` (105), `4057c43` (106), `0c66c16` (107), `bc20954` (108) |
| Code | Runners `src/exp102_*` to `src/exp108_*` with `--smoke`, `--all`, `--analyse` and (except 107) `--test-effect`; shared parts in `src/flowkit/` (bases, calibration, counts, pipeline, features, lookup, members, postprocess, swap), catalogued in [src/README.md](../../src/README.md) |
| Environment | `xgboost==3.4.1` and `optuna==5.0.0` added for 103 (new packages only; production rebuilt byte-identical afterwards) |
| Raw sources | Leaderboard text and notes saved verbatim in `submissions/raw/` (morning and evening, 13 October); upload score JSON files |

Re-run any experiment from the repository root, for example:

```bash
.venv/bin/python src/exp105_pairswap_reproduction.py --smoke
.venv/bin/python src/exp105_pairswap_reproduction.py --all
.venv/bin/python src/exp105_pairswap_reproduction.py --analyse
.venv/bin/python src/exp105_pairswap_reproduction.py --test-effect
```
