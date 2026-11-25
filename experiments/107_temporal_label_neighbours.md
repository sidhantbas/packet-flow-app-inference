---
title: "107: How much would the known labels of flows opened at the same moment add? (measurement only)"
created: 2026-10-13
creator: sidhantbas
description: "Measurement of the most likely undisclosed lever behind the leaders' scores: a flow takes the label of training flows that started within about a second of it (apps open several connections at once). Capture time is excluded from our submissions; train + validation only. Both tasks; never-used seeds 2126-2130."
source:
  - 103_lookup_ensemble_reproduction.md
  - 039_capture_order.md
  - 002_cv_start_rel.md
  - ../docs/reports/leaderboard-method-reproduction.md
experiment:
  id: '107'
  tasks: [task1, task2]
  lever: data
  status: measured
  verdict: 'No such lever: copying the labels of training flows opened within 0.5-2 s is WORSE than production on every seed in both tasks (Task 1 -0.056 to -0.092, Task 2 -0.046 to -0.060); about 3 correct flows broken per fixed one; capture time does not explain the leaderboard'
---

# 107: Labels of flows opened at the same moment (measurement only)

**Status: done 2026-10-13. Protocol frozen (`0c66c16`) before any code or run.**
**Verdict: no such lever (WORSE on every seed in both tasks); capture time does not explain the leaders' scores.** Results are below the protocol. Sid, 2026-10-13: "the
leaders may not disclose what exactly happened, so we need to find out what it could be and then again ... reproduce some
experiments which have good chances to close up the gaps."

## Question and evidence

- **Why this lever:** of the 330 labelled flows, 43% start within 1 s of the previous one: apps open connections in bursts. The
  split is random, so each test flow sits among labelled flows in time. A model that copies the label of labelled flows opened at
  the same moment could gain far more than any feature change.
- **What was measured before, and why it is not this:** 039 used capture order alone (0.50) and as a feature (−0.040 / −0.015);
  103 smoothed **predictions** among held-out flows only (−0.021 / −0.016). Neither used the **known labels** of time neighbours.
  LLM_ops's "same-session neighbours" note is consistent with this lever; other leaders may use it without saying so.
- **Rule status:** capture time is excluded from our submissions (our rule, 039, 002). This is a measurement on train +
  validation only, to know what the lever is worth and whether it can explain the leaderboard. Using it would need the user to
  change the rule.

## Frozen design (each task)

For each held-out flow i, neighbour votes $v_c = \sum_{j} w_{ij}\,[y_j = c]$ over **training-fold** flows j, with
$w_{ij} = \exp\left(-(t_i - t_j)^2 / 2\sigma^2\right)$ and t = `start_rel`. Let $W = \sum_c v_c$ and $s = \max_c v_c / W$.

| Arm | Labels |
|---|---|
| P | Production (Task 1 `task1_cross_task`, Task 2 `task2_model`) |
| N05 | Production, overridden by the top neighbour class where W ≥ 0.5 and s ≥ 0.8; σ = 0.5 s |
| N10 | Same, σ = 1.0 s |
| N20 | Same, σ = 2.0 s |
| NN | The label of the single nearest training flow in time alone (no model) |

- Thresholds (W ≥ 0.5, s ≥ 0.8) and the three σ are fixed now; nothing is tuned.
- **Folds:** repeated stratified 5 × 10 at cv_seeds **2126-2130** (0 runs in `results/`); model seed = fold index.
- **Reported:** Δ vs P per arm and seed; the share of flows overridden and how often an override is right; per-class effects.
- **Test set:** nothing is built (excluded signal).

## Reading

- If an N arm gains several points, the lever can explain much of the gap to the leaders; the result goes to the user as a rules
  decision with its compliance risk (capture time, condition 1 reading, organisers' "statistical packet-flow features" framing).
- If it gains little, capture time does not explain the leaderboard either, and the gap stays unexplained by legitimate means.

## Boundaries

Train + validation labels and `start_rel` only; test features and labels not used. Task 2 arms read `start_rel` from the Task 2
file. No upload, no production change.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-13 | Protocol frozen and committed | before any code or run |
| 2026-10-13 19:15 | Runner committed (`f6a3456`); smoke checks | neighbour votes behave as expected on a toy example; `start_rel` identical in both task files |
| 19:20-19:52 | P, N05, N10, N20, NN × 2 tasks × cv_seeds 2126-2130 (`--all`) | 50 runs `…_107_<T1|T2>_<arm>_s<seed>` |
| after the runs | `--analyse` | `experiments/107_evidence/analysis.json` |

No deviation from the frozen protocol. Nothing was built for the test set.

### Commands

```bash
.venv/bin/python src/exp107_temporal_label_neighbours.py --smoke
.venv/bin/python src/exp107_temporal_label_neighbours.py --all
.venv/bin/python src/exp107_temporal_label_neighbours.py --analyse
```

## Results (mean of five never-used seeds; WORSE on every seed in every arm)

| Arm | Task 1 Δ vs P | Flows changed: fixed / broken | Task 2 Δ vs P | Flows changed: fixed / broken |
|---|---:|---|---:|---|
| N05 (σ 0.5 s) | −0.056 | 318 / 988 | −0.058 | 446 / 953 |
| N10 (σ 1.0 s) | −0.077 | 398 / 1222 | −0.046 | 605 / 1121 |
| N20 (σ 2.0 s) | −0.092 | 292 / 1314 | −0.060 | 451 / 1074 |
| NN (nearest flow in time only) | −0.351 | 770 / 5588 | −0.260 | 1071 / 5119 |

## Verdict

- **The lever does not exist in this data.** Copying the labels of training flows opened at the same moment breaks about three
  correct predictions for every one it fixes, in both tasks and at every time scale. The nearest flow in time alone is a poor
  predictor (−0.35 / −0.26 against production).
- **Why:** labels follow the destination, not the app on screen (041). When one app is in use, the phone opens connections to
  several services at once (an Instagram session also contacts facebook and google servers), so flows opened together often carry
  different labels.
- **For the leaderboard question:** capture time cannot explain the leaders' scores, whether as prediction smoothing (103) or as
  label copying (here). Our rule stays as it is, and no rules decision is needed. Status: measured.
