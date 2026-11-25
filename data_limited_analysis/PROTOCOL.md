---
title: "Data-limited analysis: frozen protocol"
created: 2026-10-10
creator: sidhantbas
description: Settings for the data-limited residual-error analysis (user brief of 2026-10-10), fixed and committed before any phase is run; results go to REPORT.md in this folder.
relation:
  - ../experiments/079_pipeline_audit.md
  - ../experiments/090_stamp_catalogue.md
  - ../experiments/092_training_pile_cleaning.md
---

# Data-limited analysis: frozen protocol

Fixed 2026-10-10 before Phases 1-5 were run (the baseline reproduction had run: `baseline.json`). The production pipeline is
not modified; everything lives in this folder. No submissions are left; results inform the report and future work only.

## Decisions taken with the user (2026-10-10)

| Question | Decision |
|---|---|
| Baseline reproduction of 88.11 | Not possible: 88.11 is a one-off leaderboard score on 81 test flows; CV gives 80.16 ± 4.86 (that pipeline) and 80.90 ± 4.74 (production). Reported and accepted |
| Baseline pipeline | **Current production**: Task 1 `models.task1_bundle` (089), Task 2 `models.task2_model` (014), production features `cv.TASK_FEATURES` |
| "Beats the baseline" | Paired on identical folds: mean paired Δ score **> one SD of the paired fold differences** (ddof 1); otherwise a tie |
| Label audit tool | Own confident-learning code (no package installs into `.venv`) |

## Common settings

- CV: `RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=2026)` on the 330 labelled flows (train + validation);
  model seed = fold index (`cv.evaluate`). Both tasks share flows, order and splits.
- Score per fold = 50 × macro F1 (Task 1) + 50 × macro F1 (Task 2). A Task-1-only variant keeps the baseline's Task 2 fold
  scores, and vice versa, so Δ score is that task's 50 × Δ macro F1.
- Test rows: only in Phase 5 as unlabelled features (as experiment 025); never labels, never for selection.
- Every result is reported as mean ± SD; seeds are written into each phase's JSON.

## Phase 1: learning curve

Fractions 0.2, 0.4, 0.6, 0.8, 1.0 of each outer training fold (stratified, `StratifiedShuffleSplit`; at least 2 rows per class,
topped up at random from that class), subsample seeds 0, 1, 2 (one draw at 1.0). Validation = the full held-out fold;
training score = score of the model on its own training subset. Power law fitted to the mean validation score:
$S(n) = a - b\,n^{-c}$ (`scipy.optimize.curve_fit`, $a \le 100$, $b > 0$, $0 < c \le 3$), $n$ = training rows per fold.
Reported: plateau $a$, and rows needed for +1 and +2 points over $S(n_{100\%})$. Verdict: **sample-limited (rising)** if the paired
gain 80% → 100% exceeds one SD of its paired fold differences, else **flat**.

## Phase 2: label quality

- Probabilities: balanced `models.SoftVote` on each task's production columns, out-of-fold over the 5 × 5 CV, averaged per flow
  over repeats (the production pipeline decides by rules and has no single probability vector).
- Suspicion = highest probability of another class − probability of the given label. Confident-learning flag: $p_\text{given} <
  t_\text{given}$ and some other class $k$ has $p_k \ge t_k$, $t_j$ = mean probability of class $j$ over flows labelled $j$.
- CSV per task: features, given label, predicted label, probabilities, suspicion, flag; sorted by suspicion.
- Sensitivity: inside each outer training fold, suspicion from an inner 5-fold SoftVote (seed = fold index); remove the top 1%,
  2% and 5% of training rows (rounded up), no class protection; retrain production; paired comparison per task. An estimate of
  what noise costs, never adopted.

## Phase 3: overlap region and acquisition spec

Overlap region = flows whose averaged out-of-fold margin (top-1 − top-2 probability, Phase 2) is below 0.25, plus every facebook
and instagram flow. Profile: classes, top-1/top-2 class pairs, transport, opening shape, and standardised mean differences of the
production columns inside vs outside. The only unlabelled rows are the 81 test flows, whose labels can never be obtained, so
no labelling list is exported; a written acquisition spec instead.

## Phase 4: feature gaps

- Confusable pairs: mutual nearest neighbours with different labels (log1p, standardised production columns, Euclidean);
  summarised by class pair, transport, opening shape and the columns that differ most and least.
- Permutation importance of the production pipeline on the held-out overlap rows vs all held-out rows: each column permuted
  across the held-out fold (seeds 0, 1, 2), drop in accuracy, mean over folds.
- Hypotheses derivable from existing columns, tested as extra columns on top of production (paired, tie rule above):

| Id | Extra columns | Tasks |
|---|---|---|
| H1 | Decoded opening stamps (090): client first packet, first message, SYN-ACK, reply, smallest / largest decoded up and down size (−1 if not decodable) | 1, 2 |
| H2 | Tempo change after the opening: rest mean gap / opening mean gap; rest mean down size / opening mean down size | 1 |
| H3 | Burst intensity: packets per burst and bytes per burst (whole flow; Task 2 on its 5 packets) | 1, 2 |
| H4 | Size asymmetry and spread: mean up − mean down size; std / mean per direction | 1, 2 |
| H5 | Opening share: opening bytes / total bytes; opening duration / total duration | 1 |

## Phase 5: semi-supervised and constraints

- Self-training: unlabelled pool = the held-out fold's features + the 81 test rows' features; a balanced SoftVote trained on the
  outer training fold pseudo-labels pool rows with probability ≥ 0.9; production is retrained on training + pseudo-labelled rows.
- Monotonic constraints: in the LightGBM member of the two Task 1 pairwise verifiers only (binary, so a direction is defined).
  Assumed (to be verified by the user): google-vs-x, P(x) **decreasing** in `transport` (UDP = 1) and in
  `p5_mean_pkt_size_up`; google-vs-instagram, P(instagram) **increasing** in `burst_count` and in `bytes_down`. Multi-class
  members and the Task 2 pair stage stay unconstrained (no class-independent direction exists).
- External resources: listed only; nothing downloaded (091 already covers the closest public dataset).

## Deliverable

`REPORT.md` and `figures/` in this folder; phase outputs as JSON and CSV next to their scripts.

## Addendum (2026-10-10, before running): risk–coverage analysis

User request: a reject-option view for the report (the challenge itself requires a label for every flow, so this changes no
submission). Same CV as above. Per held-out fold: labels from production (`cv.evaluate` out-of-fold predictions); confidence
from a balanced `SoftVote` trained on the same training fold (seed = fold index) on the production columns, as the margin
top-1 − top-2 probability (production decides by rules and has no single probability). Abstain on the least confident 0, 5, 10,
20 and 30% of each held-out fold (rounded up). Reported per task and for the total: accuracy and macro F1 (labels present) on the
kept flows, mean ± SD over the 25 folds; the share of production's errors that fall in the abstained set; the abstained flows by
true class. Figure: `figures/risk_coverage.png`.

## Addendum 2 (2026-10-10, before running): decision-headroom audit

User: focus on the decision side. Measurement of how much any decision rule could gain on top of production's labels, given the
probabilities. Same 5 × 5 CV. Per held-out fold: production labels (`cv.evaluate`) and a balanced `SoftVote` probability vector
(same training fold, seed = fold index), ranks by probability. Bounds (per task; macro F1 mean ± SD over folds; total score):

- **B0** production as is.
- **B1 oracle top-2:** every production error whose true label is the SoftVote's top-1 or top-2 class is corrected.
- **B2 realistic:** as B1, but only where the top-1 − top-2 margin is below 0.25.
- **Unreachable:** errors whose true label ranks third or lower (no re-ranking of the top two can fix them).

Also reported: the reachable errors by true class and by (true, predicted) pair. Reading fixed now: if B2 − B0 is below 1 point of
total score, the decision side is closed; otherwise a parameter-free decision rule aimed at that headroom is proposed under its own
protocol. Output: `decision_headroom.json`, `figures/decision_headroom.png`.
