---
title: "067: Facebook/Instagram twins: tuned Facebook threshold and a plain twins-to-facebook rule"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for two Task 1 decision changes aimed at Facebook/Instagram twin flows, with rule v2 on three seeds and a pre-registered flow-level paired check.
source:
  - 034_meta_gate.md
  - 043_topk_facebook.md
  - 061_task1_f1_threshold_rule.md
  - 039_capture_order.md
experiment:
  id: '067'
  tasks:
  - task1
  lever: decision
  status: rejected
  verdict: 'Tuned facebook threshold (chosen cutoff 0.20-0.80 across folds) and a twins-to-facebook rule: no gain'
---

# 067: Facebook/Instagram twins: tuned Facebook threshold and a twins-to-facebook rule

**Status: done 2026-10-09. Protocol frozen (`bed6f38`), amended before execution (`2483448`).**
**Verdict: TH rejected (no gain on 3 seeds; flow check unproven); THTW rejected (adds nothing beyond TH). Production unchanged.** Results are below.
Do not edit the frozen sections after execution starts. Time box (user): today only; unproven results are logged as
unproven and work moves to problem 4.

## Question

Can a Facebook-favouring decision for Facebook/Instagram flows raise Task 1 macro F1, given that facebook (11 flows) is
worth more per flow than instagram (19 flows) under macro F1?

## Evidence before this experiment (flow audit, 2026-10-09, production CV)

- Instagram: right 96% of the time when its nearest training flow is instagram, 16% when not.
- Facebook: 2 of 11 flows always right, 1 always wrong, 8 right 50-90% of the time (unstable).
- Cross-app twins: facebook `flow_000368` ↔ instagram `flow_000379` (distance 0.91); facebook `flow_000809` /
  `flow_001168` ↔ instagram `flow_001185` (0.63-0.68). Distances: 16 gate-2 columns, log1p, standardised.

## User requests and how they are handled

| Request | Handling |
|---|---|
| Twin feature from start times ("another Meta-like flow started within 1 s"), if the rules allow | **Not used.** Our rules treat capture time and order (`start_rel`, `flow_id`) as off-limits (039, BACKLOG "Off-limits"; 002 found `start_rel` acts as recording-time leakage). Twins here are feature-space twins only. |
| Calibrated probabilities | **Not added.** The decision is one threshold on one score; calibration is monotone, so a threshold tuned on out-of-fold predictions gives identical decisions. Stated here, not tested. |
| Tune a Facebook threshold on out-of-fold CV predictions | Arm **TH**, tuned by **nested** CV inside each training fold (tuning on the same out-of-fold predictions that are scored would overstate the gain; 004). |
| Plain twins-to-facebook rule | Arm **TW**. |
| Rule v2 with at least 3 seeds; flow-level paired check | Both arms on cv_seeds 2026, 2027, 2028; check below. |

## Frozen arms

Both start from the production prediction of `models.task1_meta_gate` (features `cv.task1_with_prefix_features`) and
change only flows whose production label is facebook or instagram; the production rule "flows the 17-column SoftVote calls
facebook stay facebook" is applied last, as in production.

- **TH (tuned threshold):** score r = p_fb / (p_fb + p_ig) from the whole-flow expert. A Meta-labelled flow becomes
  facebook if r ≥ θ, else instagram. θ = 0.5 reproduces production exactly. θ is chosen inside each outer training fold by
  an inner 5-fold stratified CV (shuffle, random_state = model seed) of production: the θ in {0.20, 0.25, …, 0.80} with the
  highest inner macro F1; ties go to the θ closest to 0.5.
- **TW (twins to facebook):** a Meta-labelled flow becomes facebook if its nearest training-fold **facebook** flow is within
  distance 1.0 (16 gate-2 columns `capture_checks.PROX_COLS`, log1p, standardised on the training fold). Nothing tuned.

## Amendment before execution (user, 2026-10-09; no run had started)

1. **Order:** TH runs first on all three seeds; it is the baseline the twin rule must beat.
2. **The standalone TW arm is replaced by THTW** = TH, then the twin rule on the Meta-labelled flows, then the
   production facebook-keep rule. THTW is kept only if it adds something beyond TH: rule v2 BETTER **vs TH** on all three
   seeds, plus the flow-level check vs TH. It is also reported vs production.
3. **Twins at test time:** each flow to be predicted is compared only with the **facebook flows of the training data**
   (`self.ref_` = the training fold; at submission time the train+validation set). Test flows are never compared with each
   other, so no test-to-test information is used.
4. **Distance fixed now and not changed after results:** the 16 gate-2 columns (`capture_checks.PROX_COLS`), log1p,
   standardised with the training-fold mean and standard deviation, Euclidean, cutoff 1.0.
5. Calibration: as above, one threshold on one score makes it redundant; not added.

## Frozen decision rules

- Each arm vs production on cv_seeds 2026, 2027, 2028 (references: champion `20261001T173854Z_034_meta_gate`;
  `20261009T172902Z_062_production_s2027`; `20261009T173025Z_062_production_s2028`).
- **Adopt** TH only with rule v2 BETTER vs production on all three seeds; THTW only with rule v2 BETTER vs TH on all three
  seeds (and the user's approval, as for any production change).
- **Flow-level paired check** (evidence only; pre-registered reading), pooled over the three seeds:
  1. per facebook/instagram flow, the share of repeats it is right, old vs new (averaged per flow first);
  2. McNemar exact test on flows where the per-flow majority (right in ≥ 50% of repeats) differs: fixed vs broken;
  3. paired bootstrap over flows (2,000 resamples of the 330 flows, the same resample for every repeat and seed) of the
     facebook F1 and instagram F1 differences, 95% interval;
  4. a table per flow: old share, new share, fixed / broken / unchanged.
  If the 95% interval crosses zero, the reading is **unproven**, whatever the point estimate.
- One-paragraph verdict per arm: adopt, reject, or unproven.

## Boundaries

Train+validation only; no capture time or order; production frozen at 5eb9a8b until the user approves a change.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `bed6f38`, before any code change or run |
| 2026-10-09 | Amendment (user) and runner + `src/flowcheck.py` committed, before any run | `2483448`; smoke test: θ = 0.5 and a disabled twin rule reproduce production exactly; on one split TH chose θ = 0.25 (2 changes), the twin rule changed 0 |
| 18:21-18:24 | TH on 2026, 2027, 2028 vs production | runs `20261009T182114Z_067_TH`, `…182221Z…_TH_s2027`, `…182327Z…_TH_s2028` |
| 18:25-18:28 | THTW on 2026, 2027, 2028 vs TH | runs `20261009T182508Z_067_THTW`, `…182615Z…_THTW_s2027`, `…182721Z…_THTW_s2028` |
| after the runs | Flow checks (pooled over 3 seeds) | `experiments/067_evidence/flowcheck_*.md` |
| after the runs | θ recomputed (not logged by runlog): all 50 folds of 2026 and the full data | `experiments/067_evidence/thresholds.json` |

No deviation from the amended protocol.

## Results

### TH (tuned facebook threshold) vs production

| Seed | Δ macro F1 | Wins / losses / ties | Verdict | facebook | instagram |
|---|---:|---|---|---:|---:|
| 2026 | −0.0073 | 2 / 7 / 41 | INCONCLUSIVE | −0.023 | −0.021 |
| 2027 | −0.0002 | 4 / 6 / 40 | INCONCLUSIVE | −0.002 | +0.001 |
| 2028 | −0.0016 | 4 / 5 / 41 | INCONCLUSIVE | +0.011 | −0.020 |

Chosen θ: in the 50 folds of 2026 it spreads from 0.20 to 0.80 (0.20 ×8, 0.25 ×3, 0.30 ×4, 0.35 ×2, 0.40 ×3, 0.45 ×3,
0.50 ×15, 0.55 ×2, 0.60 ×1, 0.65 ×3, 0.70 ×4, 0.80 ×2; median 0.50). On all train+validation (seed 0) it is 0.25.

Flow check (pooled over 3 seeds): McNemar fixed 1 (facebook `flow_000368`, 0.47 → 0.57), broken 0, p = 1.000.
Facebook F1 −0.009 [−0.037, +0.012], instagram F1 −0.008 [−0.030, +0.008]: both **unproven**. Largest per-flow changes:
instagram `flow_000477` 1.00 → 0.80, `flow_000359` 0.83 → 0.63.

### THTW (TH + twins to facebook) vs TH

| Seed | Δ macro F1 | Wins / losses / ties | Verdict | facebook | instagram |
|---|---:|---|---|---:|---:|
| 2026 | −0.0002 | 1 / 2 / 47 | INCONCLUSIVE | −0.008 | +0.007 |
| 2027 | −0.0007 | 2 / 5 / 43 | INCONCLUSIVE | −0.017 | +0.013 |
| 2028 | +0.0002 | 2 / 5 / 43 | INCONCLUSIVE | −0.012 | +0.013 |

Flow check vs TH: McNemar fixed 0, broken 0. Facebook F1 −0.016 [−0.056, +0.000], instagram F1 +0.012 [+0.000, +0.040]:
both **unproven**. Vs production: facebook −0.026 [−0.078, +0.009], instagram +0.003 [−0.026, +0.035], unproven.

## Verdict

**TH: reject.** The tuned threshold gives no gain on any of three seeds and the flow check is unproven for both classes.
The chosen θ is unstable (0.20-0.80 across folds): with about nine facebook flows per training fold, inner CV cannot fix a
threshold, as 004 and 033 found for searched parameters. **THTW: reject.** Within the fixed cutoff it changes very few
flows (3-7 non-tied folds) and only moves errors between facebook and instagram; it adds nothing beyond TH. Twins were
found only against training facebook flows, never test-to-test. Problem 3 (facebook/instagram siblings) is closed for
today, per the time box; work moves to problem 4 (facebook vs google).
