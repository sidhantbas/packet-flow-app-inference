---
title: "118 (H-T): Does opening timing help decide facebook vs instagram among Meta flows in Task 2?"
created: 2026-10-19
creator: sidhantbas
description: "Frozen test of hypothesis H-T: adding the five opening-timing columns to Task 2's facebook/instagram specialist (production routing unchanged) improves the pair decision and end-to-end macro F1, under ordinary, exact-opening grouped and capture-session grouped folds, seeds 2171-2175."
source:
  - 007_drop_timing.md
  - 096_task2_timing_tiebreaker.md
  - 115_identifiability_and_artefacts.md
  - 117_grouped_109b.md
  - ../notebooks/code-walkthrough/05-facebook-instagram.ipynb
experiment:
  id: '118'
  tasks: [task2]
  lever: features
  status: rejected
  verdict: 'H-T falsified: timing lowers the facebook/instagram AUC in every fold family (−0.028 ordinary, −0.074 exact, −0.062 session) and end-to-end Task 2 macro F1 on every seed of every family (−0.031, −0.013, −0.021; rule v2 WORSE 15 of 15); 0 test changes. Side finding: session-grouped folds barely lower production (0.74 vs 0.77) while exact-opening groups do (0.48)'
---

# 118 (H-T): Conditional timing information for facebook vs instagram

**Status: done 2026-10-19. Protocol frozen (`f7760f5`) before any code or run.**
**Verdict: H-T falsified. Opening timing carries no usable facebook/instagram information; it makes the specialist worse in every
fold family and on every seed.** Results are below the protocol.
Do not edit the frozen sections after execution starts. Sid, 2026-10-19, hypothesis H-T (verbatim in the user's message):
"Although opening-timing features reduce performance in global six-class classification (Experiment 007), they contain additional
predictive information about Facebook versus Instagram among Meta-like flows. Adding timing features to a leakage-safe Meta
specialist will improve Facebook–Instagram discrimination over an otherwise identical specialist using the existing features alone.
This improvement will remain positive under duplicate-aware evaluation and, where capture metadata permits, evaluation across
held-out capture groups. The effect must be reproducible across prespecified seeds, must not depend on a small number of repeated or
near-duplicate flows, and must demonstrate practical value in end-to-end evaluation using the production routing gate."

## Evidence before the run

- **Against:** a facebook/instagram SoftVote with timing scored two-app AUC 0.544 vs 0.596 without (notebook 5, part 2; balanced
  weights, cv_seed 2026). 096 could not test timing inside Meta openings (too few rows per label). 007: timing hurts the 6-app model.
- **For:** timing breaks all three exact facebook/instagram ties of the 12-column view (10 flows; 2026-10-19 enumeration). Whether it
  breaks them *informatively* is the question.

## Frozen design

**Arms** (Task 2 file only; both arms receive the same 17-column rows):

| Arm | Routing (unchanged) | Facebook/instagram specialist |
|---|---|---|
| P2 | production 014: balanced SoftVote on the 12 production columns | unweighted SoftVote on the 12 production columns (`models.task2_model`) |
| T | identical | unweighted SoftVote on the 12 columns **plus** `duration`, `mean_iat`, `std_iat`, `max_iat`, `min_iat` (`models.PairSpecialist(base_cols=12 columns, spec_all_cols=True)`) |

**Fold families** (seeds 2171-2175, 5 folds × 10 repeats, model seed = fold index, identical splits for both arms):

| Family | Construction |
|---|---|
| ordinary | `RepeatedStratifiedKFold` (as production's evaluation) |
| exact | `StratifiedGroupKFold`, groups = identical 12-column openings (117's primary grouping) |
| session | `StratifiedGroupKFold`, groups = capture sessions: labelled flows in `start_rel` order, a new session after a gap > 30 s (28 sessions; facebook in 6, instagram in 9; 1-4 facebook and 3-5 instagram per test fold). `start_rel` builds folds only, never a model input |

**Measurements:**

1. *Descriptive:* single-column AUC of each timing column for facebook vs instagram on the 30 Meta flows, and inside the three tied
   vectors.
2. *Pair level:* the two specialists alone on the 30 Meta flows, in each family (folds built on the Meta subset with the same rules):
   two-app AUC and macro F1, mean over 5 seeds × 10 repeats.
3. *End to end:* Task 2 macro F1 of P2 and T in each family and seed; paired Δ = T − P2 (rule v2), per-class F1, changed predictions
   as predictions / distinct flows / groups, net gain by group and by flow.

## Decision rule

**Supported** only if all hold:

- (a) pair-level AUC of T exceeds P2's in all three families;
- (b) end-to-end Δ > 0 on all 5 seeds in all three families, with no seed rule v2 WORSE;
- (c) in each family, the pooled net gain comes from ≥ 5 distinct flows and no single group holds more than half of it.

**Falsified** if end-to-end Δ ≤ 0 on at least 3 of 5 ordinary seeds, or pair-level AUC of T is below P2's on ordinary folds.
**Otherwise** inconclusive.

Supported is evidence only. A production change needs the user's decision; an upload also needs the upload rule (rule v2 on
never-used seeds and at least 3 test predictions different from every earlier upload). No decoded sizes are used, so condition 3
does not arise.

## Boundaries

Task 2 reads only `task2_realtime_prefix5/` files (features, timing, `start_rel` for fold construction). Train + validation labels
only; test features only for the test-effect count. No production or submission change.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-19 | Session-grouping structure inspected (start times and labels only, no model results) | gap > 30 s chosen: the strictest threshold that keeps facebook and instagram in every test fold |
| 2026-10-19 | Protocol frozen and committed | before any code change or run |
| 2026-10-19 | Runner committed (`16a571e`); smoke check | 0 groups in both training and validation (exact: 123 groups; session: 28) over 250 folds each; T's routing uses exactly the 12 production columns; T equals P2 wherever the routing does not call Meta |
| 2026-10-19 | 30 end-to-end runs `…_118_<arm>_<family>_s<seed>`; `--pair`; `--analyse`; `--test-effect` | `118_evidence/end_to_end.json`, `pair_level.json`, `test_effect.json`; every run read only Task 2 files and both arms of each seed share a fold signature (asserted) |

No deviation from the frozen protocol.

## Results

Evidence: [`pair_level.json`](118_evidence/pair_level.json), [`end_to_end.json`](118_evidence/end_to_end.json),
[`test_effect.json`](118_evidence/test_effect.json).

**1. Descriptive** (single-column AUC, facebook vs instagram; 0.5 = no signal): on the 30 Meta flows `duration` 0.574,
`mean_iat` 0.574, `std_iat` 0.526, `max_iat` 0.531, `min_iat` 0.656; inside the 10 tied flows
(3 facebook, 7 instagram) duration 0.571, mean_iat 0.571, std_iat 0.571, max_iat 0.571, min_iat 0.5. None reaches the 0.70 signal level.

**2. Pair level** (the specialists alone on the 30 Meta flows; mean over 5 seeds × 10 repeats):

| Fold family | AUC, 12 columns | AUC, + timing | Δ AUC | Two-app macro F1 |
|---|---:|---:|---:|---|
| ordinary | 0.590 | 0.562 | **-0.028** | 0.642 → 0.562 |
| exact | 0.671 | 0.597 | **-0.074** | 0.649 → 0.590 |
| session | 0.712 | 0.650 | **-0.062** | 0.707 → 0.631 |

**3. End to end** (Task 2 macro F1, production routing; mean over seeds; Δ = T − P2 ± sd over 5 seeds):

| Fold family | P2 | T | Δ | Seeds WORSE | facebook F1 | instagram F1 | Flows net improved / worsened |
|---|---:|---:|---:|---:|---|---|---|
| ordinary | 0.766 | 0.735 | **-0.0306 ± 0.0080** | 5 of 5 | 0.47 → 0.41 | 0.74 → 0.63 | 1 / 12 |
| exact | 0.483 | 0.470 | **-0.0133 ± 0.0039** | 5 of 5 | 0.31 → 0.26 | 0.58 → 0.55 | 2 / 5 |
| session | 0.741 | 0.721 | **-0.0205 ± 0.0000** | 5 of 5 | 0.55 → 0.46 | 0.79 → 0.74 | 0 / 2 |

Google F1 is unchanged everywhere (routing unchanged). The session family gives the same Δ on every seed: with 28 sessions the
grouped splits repeat the same partitions. **Test effect:** T changes 0 Task 2 test predictions.

## Verdict

**H-T is falsified** by both pre-registered criteria: timing lowers the pair-level AUC on ordinary folds (−0.028), and the end-to-end
Δ is negative on 5 of 5 ordinary seeds. It fails every support condition in every family: the AUC falls in all three, macro F1 falls
on all 15 family-seeds (rule v2 WORSE on each), and facebook and instagram F1 both fall.

1. **Opening timing is noise for this pair too**, as it is for the six apps (007): no timing column separates facebook from
   instagram (best single-column AUC 0.66, `min_iat`), not even inside the tied vectors (≤ 0.57). Breaking the exact ties with timing
   is breaking them at random.
2. **The facebook/instagram ceiling in Task 2 is set by the data:** opening sizes collide (115, the 2026-10-19 enumeration), and
   the only other Task 2 information, timing, carries none.

**Side finding (evaluation):** keeping capture sessions apart barely lowers production Task 2 (0.74 vs 0.77 on ordinary folds),
while keeping identical openings apart lowers it to 0.48 (117). The memorised openings recur **across** sessions: they behave like
stable traits of each app's client on the capture devices, not like leakage between neighbouring flows.
