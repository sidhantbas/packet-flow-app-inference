---
title: "126: Do Meta flows leak into Task 1's non-Meta predictions, and can a volume-based rescue pull them back safely?"
created: 2026-10-21
creator: sidhantbas
description: "Frozen Task 1 audit of production's Meta leak (true facebook/instagram flows predicted as google, mozilla, x or youtube) with their volume profile, then a pre-registered family of volume-based rescue rules on top of production (6 arms on cv_seed 2026), the best arm confirmed on never-used cv_seeds 2186-2190, and the test flows it would change counted without labels."
source:
  - 099_class_count_deficit.md
  - 100_cross_task_meta_rescue.md
  - 112_layer_audit.md
  - 119_leader_meta_decomposition.md
experiment:
  id: '126'
  tasks: [task1]
  lever: hierarchy
  status: rejected
  verdict: 'The Task 1 Meta leak is small (3 of 30 Meta flows per repeat, mostly instagram called youtube or x) and the leaked flows are light (median 592 B down vs 22 kB for Meta flows called Meta), so they look like x/google, not Meta; every volume rescue arm loses (Δ −0.003 to −0.034, instagram −0.013 to −0.137): at threshold 0.5 a rescue reaches 2 leaked predictions but 86 true non-Meta ones; no arm selected, no confirmation or test change; Task 1 Meta is at its limit on these features'
---

# 126: Task 1 Meta-leak audit and volume rescue

**Status: done 2026-10-21. Protocol frozen (`7264dc2`) before any code or run.**
**Verdict: the leak is small and the leaked Meta flows are light, not heavy; no volume rescue helps.** Results are below the
protocol. Do not edit the frozen sections after execution starts.
Sid, 2026-10-21: "go ahead and run experiment 1" (the Meta-leak audit proposed after the leaderboard arithmetic: our Task 1 errors
cost about 1 point each because they hit the tiny Meta classes; 099 found Task 1 predicts 2 instagram test flows where the training
mix suggests about 5). **Measurement first:** no production change; a candidate only through the confirmation and the upload rule.

## Questions

1. **Leak size:** how many true facebook/instagram flows does production call google, mozilla, x or youtube (cross-validation)?
2. **Profile:** do those flows look Meta by volume (heavy, bursty), or like the class they were called?
3. **Rescue:** does a volume-based rule that moves non-Meta calls back into Meta fix more than it breaks?
4. **Test reach:** how many of the 81 test flows would the rule change (features only, no labels)?

## Frozen design

**Volume columns** (the five strongest facebook/instagram separators measured on the 330 labelled flows on 2026-10-21, before
this protocol; their choice therefore saw all labelled flows, disclosed here): `bytes_down`, `packet_count_down`, `bytes_up`,
`burst_count`, `packet_count_up`.

**Part A, audit** (production's champion run `20261012T154049Z_100_production_check_s2026`, out-of-fold, 50 folds): Meta flows
predicted non-Meta, per repeat and per flow (majority over repeats), by predicted class; their volume medians against correctly
called Meta flows and against the true classes they were called; out-of-fold volume-Meta scores (below) of the leaked flows vs
true non-Meta flows.

**Part B, rescue arms** (each = production `models.TASK_MODELS["task1_static"]`, unchanged, plus one rule):

- **Volume-Meta detector:** balanced `SoftVote(seed)` on the five volume columns, Meta (facebook + instagram) vs rest, fitted on
  the training fold.
- **Pair decider:** balanced `SoftVote(seed)` on all 34 production columns, fitted on the training fold's facebook + instagram rows.
- **Rule:** a flow production calls non-Meta whose detector P(Meta) ≥ *t* becomes Meta: **IG** arms → instagram; **PAIR** arms →
  the pair decider's label.
- **Arms:** *t* ∈ {0.5, 0.7, 0.9} × {IG, PAIR} = 6 arms, cv_seed 2026, each via `record_run` against the champion (same folds).

**Selection:** the arm with the largest paired mean Δ macro F1 at cv_seed 2026, if Δ > 0; otherwise none and the experiment stops.

**Part C, confirmation** (selected arm only): never-used cv_seeds **2186, 2187, 2188, 2189, 2190**, production re-run on each seed
as reference, rule v2 per seed.

**Part D, test reach** (selected arm only, whatever Part C says): fit production and the arm on all 330 labelled flows (seed 0),
predict the 81 test flows, count changed predictions against production and against every earlier upload file
(`submissions/uploads.csv`). No test labels or test `label_counts` are read.

## Decision rule

- **Candidate:** the selected arm is rule v2 BETTER on **all five** fresh seeds **and** its test file differs from every earlier
  upload in ≥ 3 predictions (the upload rule). It would then go to the user for a decision; nothing is adopted or uploaded here.
- **Otherwise:** no candidate. Parts A and D still say how large the leak is and where the test flows sit, for the report.

## Boundaries

Train + validation only for every score; Task 2 untouched (the rule reads only Task 1 production columns); no test labels, no test
counts; production and submissions unchanged.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-21 | Protocol frozen and committed (`7264dc2`) | before any code change or run |
| 2026-10-21 | Runner committed; first audit run stopped on its own row-count check (expected 1650, the out-of-fold table has 330 × 10 = 3300 rows); check corrected, no design change | [`126_evidence/audit.json`](126_evidence/audit.json) |
| 2026-10-21 15:14-15:17 | Part B: 6 arms at cv_seed 2026 vs the champion | `results/20261021T1514*_126_*` to `20261021T1517*_126_*` |

**Parts C and D not run:** no arm has Δ > 0, so by the frozen selection rule the experiment stops (no confirmation seeds used,
no test predictions made).

## Results

**Part A, audit** (champion out-of-fold, 300 Meta predictions = 30 Meta flows × 10 repeats):

| Measure | Value |
|---|---|
| Meta predictions called non-Meta | **30 of 300 (3 flows per repeat)**: instagram 20, facebook 10; called youtube 16, x 8, google 4, mozilla 2 |
| Flows leaked in most repeats | `flow_000003` instagram → youtube/google (10 of 10), `flow_000216` instagram → youtube (9), `flow_000231` facebook → x (6) |
| Median volume, leaked flows | 592 B down, 8 packets down, 921 B up, 7 bursts, 11 packets up |
| Median volume, Meta flows called Meta | 22,453 B down, 67 packets down, 20,111 B up, 12 bursts, 56 packets up |
| Median volume, true x / google | x 3,576 B down, 8 packets; google 9,038 B down, 20 packets |
| Volume-Meta score, leaked predictions | median 0.11; ≥ 0.5 for 2 of 30, ≥ 0.9 for 1 |
| Volume-Meta score, true non-Meta called non-Meta | ≥ 0.5 for 86, ≥ 0.7 for 44, ≥ 0.9 for 8 |

**Part B, rescue arms** (Δ macro F1 vs the champion, same folds):

| Arm | Δ macro | W / L / T | Verdict | facebook | google | instagram |
|---|---:|---|---|---:|---:|---:|
| IG 0.5 | −0.0290 | 0 / 40 / 10 | WORSE | +0.000 | −0.014 | −0.137 |
| IG 0.7 | −0.0160 | 0 / 31 / 19 | WORSE | +0.000 | −0.006 | −0.076 |
| IG 0.9 | −0.0030 | 1 / 8 / 41 | INCONCLUSIVE | +0.000 | −0.000 | −0.013 |
| PAIR 0.5 | −0.0336 | 0 / 40 / 10 | WORSE | −0.073 | −0.014 | −0.091 |
| PAIR 0.7 | −0.0174 | 0 / 31 / 19 | WORSE | −0.022 | −0.006 | −0.063 |
| PAIR 0.9 | −0.0030 | 1 / 8 / 41 | INCONCLUSIVE | +0.000 | −0.000 | −0.013 |

## Verdict

**No rescue helps; Task 1's Meta handling is at its limit on the released features.**

1. **The leak is small.** Production already calls 270 of 300 Meta predictions Meta; 3 flows per repeat leak, two of them almost
   always (`flow_000003`, `flow_000216`, both instagram → youtube).
2. **The leaked flows are light, not heavy.** They download about 0.6 kB against 22 kB for the Meta flows the model gets right, and
   look like x or google flows by volume. Volume, the strongest facebook/instagram signal, points away from Meta for exactly these
   flows, so a volume rescue reaches 2 leaked predictions while catching 86 real non-Meta ones at threshold 0.5.
3. **For the test set** (099: 2 instagram predicted where the training mix suggests about 5): if the missing instagram flows are
   like the leaked CV flows, they are small flows indistinguishable from x/youtube by these columns. No rule tested here can find
   them without breaking more correct flows.

