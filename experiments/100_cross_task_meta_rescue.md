---
title: "100: When the opening model says instagram but Task 1 says a non-Meta app, should Task 1 say facebook?"
created: 2026-10-12
creator: sidhantbas
description: "Frozen test of a cross-task Meta rescue for Task 1: production 089 plus an inner copy of the Task 2 production model; flows the inner model calls instagram while 089 calls them non-Meta are relabelled facebook. Fresh ordinary seeds 2046-2050 and five twin-aware fold sets."
source:
  - 099_class_count_deficit.md
  - 089_near_miss_bundle.md
  - 087_doorman_protects_instagram.md
  - 084_pair_verifiers.md
  - 038_unused_information.md
  - 036_twin_aware.md
experiment:
  id: '100'
  tasks: [task1]
  lever: hierarchy
  status: adopted
  verdict: 'Not a pass by the frozen rule (FB BETTER on 1 of 5 fresh seeds) but positive on all 10 fresh fold sets (ordinary mean +0.011, 44 W / 22 L; twin-aware BETTER 5 of 5, pooled +0.030); IG about 0; adopted as a deliberate exception (user, 2026-10-12)'
  production: 'Task 1 since 2026-10-12: models.task1_cross_task = 089 bundle + inner 014 Task 2 model; Task 2 instagram with Task 1 non-Meta becomes facebook (1 test change: flow_000223 youtube to facebook)'
---

# 100: Cross-task Meta rescue for Task 1

**Status: done 2026-10-12. Protocol frozen (`06e23dd`) before any code or run.**
**Verdict: not a pass (BETTER on 1 of 5 fresh seeds), but positive on all 10 fresh fold sets; adopted in production as a deliberate exception (user decision 2026-10-12).** Results and adoption are below the protocol. Do not edit the frozen
sections after execution starts. User 2026-10-12: "what is the next insight that we can roll in ... the main goal is closing the
F1 score ... find a useful way to make more bold submissions."

## Question and evidence

Does Task 1 improve if a flow whose opening the Task 2 production model calls **instagram**, but which Task 1 production (089)
calls a **non-Meta** app, is relabelled **facebook**?

All evidence below was found after looking (099, post hoc), so it is the reason for this test, not part of it.

| Evidence (saved out-of-fold predictions, 089 vs 014 on the same folds) | Seed 2026 | Seed 2027 | Seed 2028 |
|---|---|---|---|
| Cases (Task 2 instagram, Task 1 non-Meta) | 12 | 16 | 24 |
| Truth facebook / instagram / other | 8 / 4 / 0 | 11 / 5 / 0 | 13 / 9 / 2 |
| Relabel facebook: Δ macro F1, W / L / T | +0.0083, 8 / 3 / 39 | +0.0145, 10 / 4 / 36 | +0.0133, 10 / 4 / 36 |
| Relabel instagram: Δ macro F1, W / L / T | +0.0008, 4 / 7 / 39 | +0.0004, 5 / 9 / 36 | +0.0029, 8 / 6 / 36 |

- **Mechanism (seed 2026 stage trace, `experiments/098_evidence/trace_all.csv`, 12 cases):** 6 cases were inside Meta after the
  Meta gate and were pushed out by production's own instagram protections: 5 gate calls of instagram (true facebook) reverted
  by 087's rule to the two-clerks label (google), 1 (true instagram, flow_000477) reverted to mozilla. 2 (true instagram,
  flow_000210 and flow_000359, whole-run expert instagram) were turned into google by 084's google-vs-instagram verifier.
  4 never entered Meta (flow_000809 twice, flow_001168, flow_000210 once). 1 left Meta at the gate.
- **Concentration:** the 52 cases come from 11 distinct flows; flow_001145 (facebook) alone gives 16. flow_000809 and
  flow_001168 are near-twin facebook fetches (035), so ordinary folds can overstate the facebook gain.
- **Why facebook, not instagram:** the facebook-vs-instagram choice of every expert is wrong on most cases (seed 2026: whole-run
  3 of 12 right, opening 4, rest-of-flow 3), and true facebook outnumbers instagram on all three seeds.
- **Earlier, related, different:** 038 (b) used Task 2's label as a tiebreaker in every close Task 1 call (margin < 0.1):
  −0.0134 against 034. This rule has no margin condition and fires only for Task 2 = instagram with Task 1 outside Meta.

## Frozen design

- **REF:** production `models.task1_bundle` (089), features `cv.TASK_FEATURES["task1_static"]`.
- **FB (primary arm):** REF unchanged, plus an inner copy of the Task 2 production model (`models.task2_model`, 014) fitted on the
  same training rows and model seed, on the 12 no-timing prefix-5 columns from the Task 2 file (the `p5_` columns already in
  Task 1's input, renamed to their Task 2 names, in Task 2's column order). If the inner model predicts instagram and REF
  predicts a class outside {facebook, instagram}, the label becomes facebook. Nothing is tuned.
- **IG (secondary, descriptive):** the same with label instagram. It cannot become a candidate.
- **Ordinary folds:** repeated stratified 5 × 10 at cv_seeds 2046, 2047, 2048, 2049, 2050 (0 runs in `index.jsonl`).
- **Twin-aware folds:** `exp036_twin_aware.twin_splits` at seeds 2046, 2056, 2066, 2076, 2086 (random states 2046-2095, disjoint
  across the five sets; never used for twin-aware folds). Arms REF and FB.
- **Reproduction check (not evidence):** FB on cv_seed 2026 against `20261010T004051Z_089_production_check_s2026` must give the
  saved-OOF result (Δ +0.0083, 8 / 3 / 39). Otherwise stop and fix before any decision seed.
- **Smoke check:** on one fold, the inner model's predictions equal the 014 champion's held-out predictions, and REF's equal
  `task1_bundle`'s.

## Decision rule

- **Pass:** FB is rule v2 BETTER than REF on all five ordinary seeds **and** FB's mean Δ over the 250 twin-aware folds is > 0.
- **On a pass:** build the Task 1 test file (test features only; the inner model's test predictions must equal the submitted Task 2
  labels), run the official loader, and list the changed flows against the ranked entry (expected from 099: only flow_000223,
  youtube → facebook). The file becomes a production candidate. Adoption and any upload need the user's approval; nothing is
  uploaded here.
- **Otherwise:** not adopted. IG is reported either way.
- **Descriptive (frozen, decides nothing):** truth and distinct flows of the FB cases on the fresh seeds; the facebook share of the
  cases in folds where REF predicts fewer instagram flows than round(fold size × training share of instagram) versus other folds
  (bearing on the test set's instagram deficit, 099).

## Boundaries

Train + validation labels only; test features only for the file. Task 2 predictions are unchanged: Task 2 reads only its own
files. The Task 1 model reads Task 2 files (allowed since 022, disclosed in the report). No test labels, no `label_counts`, no
capture time or order. Production is unchanged.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-12 | Protocol frozen and committed | before any code or run |
| 2026-10-12 15:18 | Runner committed (`eb39f02`); smoke check | REF part identical to `task1_bundle`; inner model identical to the 014 champion on fold 0 |
| 15:18 | Reproduction check, FB on cv_seed 2026 vs `20261010T004051Z_089_production_check_s2026` | Δ +0.0083, 8 / 3 / 39: equals the saved-OOF number (`20261012T151855Z_100_FB_ordinary_s2026`) |
| 15:19-15:29 | REF, FB, IG on ordinary seeds 2046-2050; REF, FB on twin-aware seeds 2046-2086 | 25 runs `…_100_{REF,FB,IG}_{ordinary,grouped}_sN` |
| after the runs | Frozen descriptive analysis (`--analyse`) | `experiments/100_evidence/analysis.json` |
| after the runs | Decision analysis of the one test flow, **outside the protocol** (decides nothing) | `src/exp100_test_ev.py` → `experiments/100_evidence/test_ev.json` |

No deviation from the frozen protocol. No test file was built (the protocol builds one only on a pass).

## Results

### FB vs REF, ordinary folds, fresh seeds (verdicts from each run's `report.md`)

| Seed | Δ macro F1 | W / L / T | Verdict | Cases (facebook / instagram) | facebook | google | mozilla | instagram, x |
|---|---:|---|---|---|---:|---:|---:|---|
| 2046 | +0.0059 | 6 / 4 / 40 | NEAR-MISS | 13 (7 / 6) | +0.018 | +0.004 | +0.002 | 0 |
| 2047 | +0.0062 | 7 / 5 / 38 | INCONCLUSIVE | 13 (7 / 6) | +0.022 | +0.005 | 0.000 | 0 |
| 2048 | +0.0150 | 10 / 5 / 35 | NEAR-MISS | 20 (15 / 5) | +0.070 | +0.007 | +0.001 | 0 |
| 2049 | +0.0073 | 7 / 5 / 38 | INCONCLUSIVE | 15 (9 / 6) | +0.033 | +0.005 | +0.002 | 0 |
| 2050 | +0.0206 | 14 / 3 / 33 | **BETTER** | 25 (17 / 8) | +0.076 | +0.007 | +0.003 | 0 |

Mean Δ +0.0110; 44 wins, 22 losses (67% of non-tied folds). No class loses on any seed (youtube +0.002 on 2050, 0 elsewhere).

### IG vs REF, ordinary folds (secondary, descriptive)

| Seed | 2046 | 2047 | 2048 | 2049 | 2050 |
|---|---:|---:|---:|---:|---:|
| Δ macro F1 | +0.0023 | +0.0021 | −0.0013 | +0.0022 | +0.0020 |
| W / L / T | 5 / 5 / 40 | 5 / 7 / 38 | 5 / 10 / 35 | 5 / 7 / 38 | 5 / 12 / 33 |

Mean +0.0015; 25 wins, 41 losses. Labelling these flows instagram does not help.

### FB vs REF, twin-aware folds

| Seed | 2046 | 2056 | 2066 | 2076 | 2086 | Pooled (250 folds) |
|---|---:|---:|---:|---:|---:|---:|
| Δ macro F1 | +0.0316 | +0.0287 | +0.0307 | +0.0306 | +0.0300 | **+0.0303** |
| W / L / T | 17 / 7 / 26 | 16 / 6 / 28 | 18 / 3 / 29 | 18 / 4 / 28 | 18 / 7 / 25 | 87 / 27 |
| Verdict | BETTER | BETTER | BETTER | BETTER | BETTER | |
| facebook F1 | +0.125 | +0.113 | +0.131 | +0.153 | +0.120 | |

The 221 twin-aware cases are facebook 143, instagram 61, google 14, youtube 3 (92% Meta). flow_000809 and flow_001168 (near-twin
facebook fetches) are cases in all 50 folds of every set: with their twin held out together, 089 never puts them in Meta, and the
rule rescues them.

### Descriptive (frozen)

- **Ordinary cases:** 86, all Meta (facebook 55, instagram 31), from 10 distinct flows (5 facebook, 5 instagram).
  flow_001145 (facebook) is 30 of the 86 (35%); then flow_000477 and flow_000210 (instagram) 11 each, flow_000799 (facebook) 9.
- **Instagram-deficit folds:** where 089 predicts fewer instagram flows than round(fold size × training share), the cases are
  facebook 35 of 64 (55%); in the other folds 20 of 22 (91%). Twin-aware: 102 of 170 (60%) vs 41 of 51 (80%). When instagram is
  under-predicted, as on the test set (099), a larger share of these flows is instagram.

### Decision analysis of the test flow (outside the protocol; decides nothing)

On the test set, exactly one flow is a case (099): `flow_000223`, Task 1 youtube (experts' mean: youtube 0.493, instagram 0.427,
facebook 0.039), Task 2 instagram. Points (50 × macro F1) for relabelling it, from the ranked entry's counts, expected counts
(validation × 81/83) and 089's precision on the fresh seeds:

| Relabel to | If it is facebook | If it is instagram | If it is youtube (089 right) | Break-even P(label right) |
|---|---:|---:|---:|---:|
| facebook | **+1.89** | −0.51 | −1.14 | 0.38 |
| instagram | −0.25 | **+1.87** | −0.87 | 0.32 |

Expected points, assuming the flow is Meta (as all 86 fresh cases were): facebook +1.03 / instagram +0.52 with the fresh case
shares (64 / 36), +0.80 / +0.71 with the deficit-fold shares (55 / 45), +0.69 / +0.81 with the distinct-flow shares (50 / 50).

## Verdict

- **Not a pass by the frozen rule:** FB is BETTER on 1 of 5 fresh ordinary seeds (the rule needs 5). The twin-aware condition holds
  (pooled +0.0303, BETTER on all five sets).
- **Direction is consistent:** Δ > 0 on all 10 fresh fold sets, no class loses anywhere, and the post-hoc seeds agree. The rule
  fires rarely (13-25 cases per 50 folds), so most folds tie and rule v2's ≥ 70%-of-non-tied test has little power. 028 was adopted
  as a deliberate exception on a weaker profile (+0.005 to +0.013, 58-65% wins).
- **Instagram label: no.** IG is about zero with more losses than wins; the facebook label carries the gain.
- **Concentration:** 10 distinct flows, one of them 35% of the ordinary cases.
- **Status: inconclusive; exception candidate.** Adoption as a deliberate exception (like 028 and 034) is the user's decision. It
  changes one test prediction (flow_000223 youtube → facebook), worth +1.9 points if right and −0.5 to −1.1 if wrong.
  Production is unchanged.
- **Upload condition:** the file would differ from the ranked entry in one flow. By the 080 precedent such a file is a label probe
  unless its model is adopted in production first (as 084 was before upload 6). Analysis and recommendation:
  [closing-the-f1-gap-2026-10-12.md](../docs/reports/closing-the-f1-gap-2026-10-12.md).

## Adoption (user decision 2026-10-12)

User 2026-10-12: "adopt 100 and build the submission file". Adopted as a deliberate exception to the frozen rule, like 028 and 034.

| Step | Outcome |
|---|---|
| Registry | `models.task1_cross_task` (`CrossTaskMetaRescue`: `task1_bundle` + inner `task2_model` on `TwoClerks.OPEN_COLS` renamed to the Task 2 names); `models.TASK_MODELS["task1_static"]` |
| Production check, cv_seed 2026 | `20261012T154049Z_100_production_check_s2026`: predictions identical to `20261012T151855Z_100_FB_ordinary_s2026`; macro F1 0.8573 (089: 0.849); new Task 1 champion |
| Production check, cv_seed 2046 | `20261012T154113Z_100_production_check_s2046`: fold scores and predictions identical to `20261012T151957Z_100_FB_ordinary_s2046` |
| Submission | `submissions/production-100-cross-task/` (`src/make_final_candidate.py --out …`) and `submissions/submission.*` (`src/make_submission.py`), JSON identical; rebuild identical; official loader passed; vs the ranked entry 1 Task 1 change (`flow_000223` youtube → facebook), Task 2 identical |
| Upload | 2026-10-12 (Sid), upload 8: Task 1 0.822 (accuracy 0.889), Task 2 0.905, total 86.36 (−0.87 vs upload 7), inside the pre-registered downside (−0.5 to −1.1). The ranked entry by the rule fixed before the score. Information only: it is never used to infer that flow's label, to change production or to choose files |

