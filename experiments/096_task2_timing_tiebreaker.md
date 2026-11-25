---
title: "096: Task 2 timing as a tie-breaker only inside ambiguous 12-feature signature groups"
created: 2026-10-11
creator: sidhantbas
description: Frozen protocol and results for testing whether the five permitted Task 2 timing columns separate apps specifically where the 12 no-timing columns are identical across labels, while production ignores timing everywhere else.
source:
  - 007_drop_timing.md
  - 004_ceilings_ensemble_thresholds.md
  - 015_mozilla_x.md
  - 031_error_audit.md
  - 036_twin_aware.md
  - ../reports/evidence-handoff/README.md
experiment:
  id: 096
  tasks:
  - task2
  lever: decision
  status: rejected
  verdict: 'Timing as a tie-breaker inside identical 12-feature groups: WORSE on 3 seeds and grouped folds, 0 errors corrected; Meta groups untestable'
---

# 096: Task 2 timing as a tie-breaker inside ambiguous signature groups

**Status: done 2026-10-11. Protocol frozen (`62dc76c`) before any code change or run.**
**Verdict: not supported. WORSE on seeds 2026-2028 (−0.0064 to −0.0085) and on grouped folds (−0.0107); 0 errors corrected; no facebook or instagram flow was ever eligible (≤ 1 facebook row per Meta conflict group).** Results are below.
Do not edit the frozen sections after execution starts. User brief 2026-10-11 (pasted): "Can the five permitted Task 2 timing
features distinguish applications specifically where the 12 no-timing features are ambiguous, even though adding timing globally
hurts macro F1?"

## 1. Has this been tested? (checked before freezing)

| Exp. | What it tested | Same hypothesis? |
|---|---|---|
| 007 | Timing added or dropped **globally** in Task 2 (dropping the 5 columns: +0.051) | No: global inclusion |
| 004, 031 | Measured the 7 conflict groups of identical 12-column vectors (80 flows) | No: measurement, no tie-breaker |
| 015 | Timing-aware mozilla/x specialist re-deciding **every** mozilla/x call (Δ ≈ 0, error swaps) | No: pair-conditioned, not signature-conditioned |
| 017 | Seen vs unseen vector routing, no timing | No |

**Untested.** The ambiguity-conditioned use of timing has not been run.

## 2. Frozen design

**Inputs:** only the Task 2 files (`task2_realtime_prefix5/`), the 17 statistical columns of `cv.basic_features`: the 12 no-timing
production columns plus `duration`, `mean_iat`, `std_iat`, `min_iat`, `max_iat`. No timestamps (`start_rel`), capture order
(`flow_id`), Task 1 data or test labels.

**Baseline:** production Task 2 `models.task2_model` (014) on the 12 no-timing columns, same seeds and folds as its champion runs.

**Candidate (arm TB):** inside each outer training fold:

1. **Signature** = the exact 12-column vector (no rounding).
2. **Ambiguous group** = a signature carried by training rows with ≥ 2 distinct labels.
3. **Supported labels** of a group = labels with **≥ 2 training rows** in that group. A group is **eligible** only if it has ≥ 2
   supported labels; otherwise it stays with the baseline (insufficient support).
4. **Tie-breaker (one specification, no sweep):** one L2 logistic regression, `C = 0.1`, `class_weight = None`, `max_iter = 5000`,
   on `log1p` of the 5 timing columns (clipped at 0), standardised with the mean and SD of its own training rows. It is trained on
   the training rows of all eligible groups whose label is supported in their group (pooled across groups).
   Unweighted on purpose: each group's majority stays the default, so timing must carry real evidence to override it.
5. **Prediction:** a held-out flow whose signature equals an eligible training group gets the supported label with the highest
   tie-breaker probability (probabilities restricted to that group's supported labels). Every other held-out flow (unseen
   signature, unambiguous signature, insufficient support) keeps the baseline label.

Routing uses only training rows and the held-out flow's own features; held-out labels are never used to define groups.

## 3. Evaluation

- Default CV: repeated stratified 5-fold × 10, through `runlog`, on cv_seeds **2026** (vs champion
  `20260930T173836Z_014_fi_same_nocw`), **2027** and **2028** (vs `20260930T173928Z_014_fi_same_nocw_s2027`,
  `20260930T173952Z_014_fi_same_nocw_s2028`). Identical folds and model seeds for both arms.
- **Decision rule (fixed now):** rule v2 BETTER on all three seeds (paired Δ > 0, ≥ 70% of non-tied folds won, ≥ 10 non-tied).
  Otherwise not supported.
- **Reported:** macro F1 and paired Δ; per-class F1 (facebook, instagram first); number of eligible held-out flows; errors
  corrected and introduced; results for eligible flows vs all other flows (other flows must be identical to the baseline, checked);
  the Δ per CV repeat (10 values, described, not treated as independent).
- **Grouped robustness check:** `StratifiedGroupKFold(5, shuffle)` × 10 (random_state = 2026 + repeat), groups = connected
  components of the 330 labelled flows whose 17 Task 2 statistical columns (log1p, standardised) lie within 0.05 of each other
  (036's method, but on Task 2 features). Both arms on these folds; reported with the number of eligible held-out flows. If fewer
  than 10 folds have an eligible flow, the check is reported as **too little evidence**. Grouping by the 12-column signature itself
  would remove every eligible flow by construction, so it is not used.

## 4. Interpretation fixed in advance

- **Improvement:** timing is conditionally useful *in this capture* inside identical-opening groups; it says nothing about
  application identity in general.
- **No improvement:** evidence against this particular clue (timing as a within-signature tie-breaker), not proof that all other
  permitted information is exhausted.
- Production is not changed, no submission is built, the leaderboard is not used.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-11 | Protocol frozen and committed | before any code change or run |
| 2026-10-11 | Runner committed; smoke test on one fold | outside eligible flows identical to the baseline; fold 0: 1 eligible group (x/mozilla/youtube), 6 eligible held-out flows |
| 23:00-23:01 | TB on cv_seeds 2026, 2027, 2028; baseline and TB on grouped folds | runs `…_096_TB`, `…_096_TB_s2027`, `…_096_TB_s2028`, `…_096_baseline_grouped`, `…_096_TB_grouped` |
| after the runs | Routing and error analysis | `experiments/096_evidence/analysis.json` |

No deviation from the frozen protocol.

## Results

### Overall (rule v2, vs production 014)

| Folds | Δ macro F1 | W / L / T | Verdict | facebook | instagram | x | youtube | mozilla, google |
|---|---:|---|---|---:|---:|---:|---:|---:|
| seed 2026 | −0.0065 | 0 / 16 / 34 | WORSE | 0.000 | 0.000 | −0.019 | −0.020 | 0.000 |
| seed 2027 | −0.0085 | 0 / 18 / 32 | WORSE | 0.000 | 0.000 | −0.025 | −0.026 | 0.000 |
| seed 2028 | −0.0064 | 0 / 13 / 37 | WORSE | 0.000 | 0.000 | −0.020 | −0.019 | 0.000 |
| grouped (Task 2 near-twins) | −0.0107 | 0 / 19 / 31 | WORSE | 0.000 | 0.000 | −0.031 | −0.033 | 0.000 |

Δ per CV repeat (seed 2026): −0.0071, −0.0051, −0.0159, −0.0073, −0.0025, −0.0095, −0.0049, −0.0024, −0.0048, −0.0048
(mean −0.0064, SD 0.0040; repeats share flows, so they are not independent observations).

### Eligible vs other flows

| Folds | Eligible held-out predictions (folds with any) | By true label | Changed | Corrected | Introduced | Eligible accuracy, baseline → candidate | Other flows |
|---|---|---|---:|---:|---:|---|---|
| 2026 | 526 (50 of 50) | x 300, youtube 176, mozilla 50 | 29 | **0** | 27 | 0.867 → 0.816 | identical to baseline |
| 2027 | 518 (50) | x 300, youtube 168, mozilla 50 | 38 | **0** | 35 | 0.865 → 0.797 | identical |
| 2028 | 521 (50) | x 300, youtube 171, mozilla 50 | 27 | **0** | 26 | 0.866 → 0.816 | identical |
| grouped | 521 (50) | x 300, youtube 171, mozilla 50 | 51 | **0** | 45 | 0.866 → 0.779 | identical |

Every change was **x → youtube** (true x, or true mozilla already called x by the baseline). The grouped check kept enough evidence
(eligible flows in all 50 folds): the near-twin groups include timing, so they do not merge identical 12-column signatures.

### Which ambiguous groups could be tested

| Conflict group (12 columns, all labelled flows) | Eligible in CV? |
|---|---|
| x 30, mozilla 5, youtube 2 (TCP 3/2, 794/140 B) | Yes, every fold (x and mozilla always ≥ 2 training rows; youtube when both its rows are in training) |
| youtube 24, google 2 (UDP 2/3, 2762/2666 B) | Only when both google rows are in training, so a held-out google flow is **never** eligible: only youtube flows can be tested |
| youtube 4, google 1; instagram 4, facebook 1; instagram 2, facebook 1; facebook 1, instagram 1; instagram 1, youtube 1 | **Never**: the minority label has fewer than 2 rows. **No facebook or instagram flow was ever eligible** |

## Verdict

**Not supported: WORSE on all three seeds and on grouped folds, 0 errors corrected, 26-45 introduced.**

- Inside the one ambiguous group with enough support (x vs mozilla, plus youtube), timing did not recover a single mozilla flow; it
  only moved x flows to youtube. The pooled tie-breaker learned youtube's timing mostly from the other conflict group (UDP,
  youtube 24 / google 2), which made youtube attractive inside the TCP group: a weakness of pooling across groups, fixed in the
  frozen design.
- **Facebook and instagram cannot be tested this way:** every Meta conflict group has at most one facebook row, so the support rule
  (≥ 2 rows per label) never lets the tie-breaker act. The question remains open for them, for lack of data, not because of
  evidence.
- Reading fixed in advance: this is evidence against timing as a within-signature tie-breaker for the x/mozilla/youtube TCP
  signature in this capture, not proof that all remaining permitted information is exhausted. A per-group variant would be a new
  protocol; with mozilla at 5 rows and every minority label at ≤ 2 elsewhere, its expected value is low.
- Production unchanged; no submission built.
