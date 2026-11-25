---
title: "124: Do process-labelled captures help Task 1 at Charles's low doses (0.10 and 0.25 of each class's weight)?"
created: 2026-10-20
creator: sidhantbas
description: "Frozen low-dose capture-training test in Charles's 20 October design: production Task 1 with Charles's 364 process-supported capture candidates added to training folds only at budgets 0.10 and 0.25 of each captured class's original training count, scored on original held-out flows over all six classes, on never-used cv_seeds 2181-2183."
source:
  - 056_capture_augmentation.md
  - 057_capture_meta_pair.md
  - 122_capture_handoff_deliverables.md
  - 123_gates_on_charles_candidates.md
  - "(teammate private repository)"
experiment:
  id: '124'
  tasks: [task1]
  lever: data
  status: rejected
  verdict: 'No signal: low-dose capture training (Charles''s design, his 364 process-labelled candidates) is Δ < 0 on 2 of 3 never-used seeds for both budgets (B10 mean −0.0066, B25 −0.0054) and lowers facebook F1 on every seed (−0.010 to −0.101); instagram gains at B25 (+0.023 mean) but do not offset facebook; capture training stays closed'
---

# 124: Low-dose capture training (Charles's design)

**Status: done 2026-10-20. Protocol frozen (`3237908`) before any code or run; runner `3c1c4e7`.**
**Verdict: no signal; correctly labelled captures at small doses still cost facebook on every seed.** Results are below the
protocol. Do not edit the frozen sections after execution starts.
**User decision (Sid, 2026-10-20, "go ahead and run 124"):** run this training test although the captures fail gate 2 (121, 123),
as in 056. The override covers this measurement only; it changes no production rule. **Measurement only:** no model change, no
submission, Task 1 only, no test data.

## Question

All earlier capture-training tests (056-058, 063) used session labels, and their doses were large (057's 10% of captured rows is
about as many facebook rows as the originals). Charles's hypothesis: correctly labelled captures at a small, bounded weight could
help. Does adding his process-supported candidates (labels confirmed by ours, 122) at budgets 0.10 or 0.25 raise Task 1 macro F1
without harming other classes?

## Frozen design

**Captured rows:** Charles's 364 candidates, profile `observed` (49 facebook, 157 instagram, 158 youtube), read with
`git show d3189ba:experiments/charles-003-capture-audit/evidence/20261020-flow-aggregates/observed/candidate_{labels,task1_features,task2_features}.csv`.
Production columns are built as for the originals: `basic_features` of the Task 1 row plus the `p5_` columns from the Task 2 row
(as 056's `captured_rows`).

**Arms** (production model `models.TASK_MODELS["task1_static"]`, unchanged):

| Arm | Training fold |
|---|---|
| P | original flows only (reference, same folds) |
| B10 | originals + for each captured class $c$, $k_c = \text{round}(0.10 \cdot n_c)$ captured rows of class $c$ |
| B25 | the same with 0.25 |

$n_c$ = the number of original flows of class $c$ in the training fold (about 9 facebook, 15 instagram, 44 youtube, so $k$ ≈ 1 / 2 /
4 for B10 and 2 / 4 / 11 for B25). The rows are drawn without replacement, a new draw per fold (`numpy` generator seeded with
`cv_seed × 1000 + fold`), and enter with weight 1, so the captured total weight per class equals budget × $n_c$, as in Charles's
formula (budget × $n_c$ / $m_c$ per row over all $m_c$ captured rows). **Deviation from his design, fixed in advance:** a random
subset at unit weight instead of all rows at fractional weight, because the production model takes no sample weights; and our
standard 5-fold × 10-repeat CV instead of his 4 folds, with all six classes scored.

**Folds:** repeated stratified 5 × 10 on train + validation (330 original flows), never-used **cv_seeds 2181, 2182, 2183**, model
seed = fold index; captured rows only ever in training folds (`cv.evaluate` `resample` hook). Every run through `record_run`,
B10 and B25 compared with P on the same seed.

## Decision rule

- **Signal:** an arm has paired mean Δ > 0 on all 3 seeds, facebook F1 not lower (pooled Δ ≥ 0), and no class losing more than
  0.01 pooled F1 (Charles: "a Facebook gain that damages Google/YouTube is not an overall improvement"). A signal only earns a
  confirmation on further never-used seeds under rule v2 and the user's decision; nothing enters production from this experiment.
- **No signal:** the low-dose design does not help with these captures; capture training stays closed for the deadline.

## Boundaries

Task 1 only (Task 2 never uses captures). Train + validation of the original data; no test data; production and submissions
unchanged. Charles's files are read, not modified.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-20 | Protocol frozen and committed (`3237908`) | before any code change or run |
| 2026-10-20 | Runner committed (`3c1c4e7`); smoke check on one training fold | same 34 columns as production; B10 adds 1 facebook, 1 instagram, 4 youtube rows, B25 2 / 4 / 10; draws deterministic |
| 2026-10-20 22:48-22:51 | Seeds 2181, 2182, 2183: P, B10, B25 (9 runs, about 23 s each) | `results/20261020T2248*_124_*` to `20261020T2251*_124_*` |

No deviation from the frozen protocol.

## Results

Paired Δ macro F1 against P on the same folds (rule v2 verdicts from `record_run`; every one INCONCLUSIVE); per-class Δ is pooled
F1 from the run reports.

| Arm | cv_seed | Δ macro | W / L / T | facebook | google | instagram | mozilla | x | youtube |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| B10 | 2181 | −0.0123 | 17 / 28 / 5 | −0.077 | +0.002 | +0.004 | +0.000 | −0.001 | −0.002 |
| B10 | 2182 | +0.0028 | 19 / 24 / 7 | −0.010 | +0.003 | +0.018 | +0.004 | +0.006 | −0.004 |
| B10 | 2183 | −0.0103 | 15 / 28 / 7 | −0.067 | +0.007 | −0.017 | +0.005 | +0.001 | +0.008 |
| **B10** | **mean** | **−0.0066** | | **−0.051** | +0.004 | +0.002 | +0.003 | +0.002 | +0.001 |
| B25 | 2181 | −0.0165 | 17 / 30 / 3 | −0.101 | −0.003 | +0.012 | +0.003 | −0.001 | −0.009 |
| B25 | 2182 | +0.0046 | 23 / 21 / 6 | −0.028 | +0.002 | +0.038 | +0.010 | +0.009 | −0.003 |
| B25 | 2183 | −0.0043 | 21 / 24 / 5 | −0.041 | −0.000 | +0.019 | −0.005 | +0.002 | −0.000 |
| **B25** | **mean** | **−0.0054** | | **−0.057** | −0.000 | **+0.023** | +0.003 | +0.003 | −0.004 |

Runs: `20261020T224829Z_124_P_s2181`, `…224852Z_124_B10_s2181`, `…224915Z_124_B25_s2181`, `…224940Z_124_P_s2182`,
`…225003Z_124_B10_s2182`, `…225026Z_124_B25_s2182`, `…225051Z_124_P_s2183`, `…225114Z_124_B10_s2183`, `…225137Z_124_B25_s2183`.

## Verdict

**No signal by the frozen rule** (Δ > 0 on only 1 of 3 seeds per arm, facebook lower on every seed); **capture training stays
closed for the deadline.**

1. **Correct labels and small doses do not rescue facebook.** One or two captured facebook rows per training fold (against about 9
   original ones) cost facebook 0.01 to 0.10 F1 on every seed. The captured facebook flows sit next to challenge google flows (123:
   only 3 of 49 have a facebook nearest neighbour), so they teach the model that google-like shapes can be facebook.
2. **Instagram does gain a little at B25** (+0.012, +0.038, +0.019; fewer instagram flows called youtube, e.g. 13 → 6 on 2183),
   less than half the size of the facebook loss (−0.057) and never enough to make the total positive on all seeds. An
   instagram-only dose was not in the protocol; it would be a new experiment, and its prior is low (it helped instagram, not the
   facebook bottleneck).
3. **Charles's question is answered for this design:** the earlier failures were not only a labelling artefact. With his own
   labels, his own extraction and his budgets, the captures still lower Task 1's weakest class.

