---
title: "082: Undersampling ensemble (EasyEnsemble-style) facebook detector"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for a facebook-vs-rest detector made of many small models, each trained on all facebook flows and an equal-size random sample of every other app, used to rescue facebook flows production misses.
source:
  - 081_fewshot_metric_learning.md
  - 034_meta_gate.md
  - 012_class_weights.md
experiment:
  id: 082
  tasks:
  - task1
  lever: imbalance
  status: rejected
  verdict: 'Undersampling-ensemble facebook detector: macro -0.005; 10 of 11 rescues wrong; gate failed'
---

# 082: Undersampling ensemble facebook detector

**Status: done 2026-10-09. Protocol frozen (`b8b10b7`) before any code change or run.**
**Result: stage-1 gate fails (macro F1 0.8269 < 0.8323; 0 facebook flows fixed; 10 of 11 rescues wrong). Stage 2 not run.** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: "try another method to improve facebook score".

## Why it differs from earlier attempts

Class weights (012, production) up-weight the same nine training facebook flows inside one model. An undersampling ensemble
(Liu, Wu and Zhou 2009, "Exploratory undersampling for class-imbalance learning") trains many small models, each on all
facebook flows of the training fold plus an equal-size random sample of each other app, and averages them. Not tried before.

## Stage 1 (cv_seed 2026, production folds)

Detector inside each training fold: 25 bags; bag b samples, without replacement, n_fb flows of each non-facebook class
(n_fb = facebook flows in the fold; all facebook flows in every bag); an `ExtraTreesClassifier` (300 trees, random_state =
fold × 100 + b) on the 34 production columns, facebook vs rest; P(fb) = mean over bags. Rescue: a flow production does not
call facebook becomes facebook if P(fb) ≥ 0.5. Production otherwise unchanged.

Measured (pooled over the 50 folds and by repeat): facebook precision / recall / F1 and macro F1, production vs rescue; facebook
flows fixed / broken (majority over repeats); other flows turned into facebook.

**Gate to stage 2 (frozen):** rescue macro F1 (mean over repeats) > production's **and** at least 2 facebook flows fixed by
majority. Otherwise stop.

## Stage 2 (only if the gate passes)

Rescue vs production on cv_seeds 2026, 2027, 2028 through `cv.evaluate` and `runlog` (references: champion and the 062
production runs). Pass: rule v2 BETTER on all three; evidence: facebook/instagram flow-level check. A pass is a submission
candidate (user approval; ranked file chosen on CV before any score).

## Boundaries

Train+validation only; no test features; nothing pretrained. Production frozen at 5eb9a8b until the user approves.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `b8b10b7`, before any code change or run |
| 2026-10-09 | Stage 1 run inline (50 folds of cv_seed 2026, 25 bags per fold, 11 s) | session scratchpad only |

No deviation from the frozen protocol.

## Stage 1 results (pooled over 50 folds)

| | Facebook precision | Facebook recall | Facebook F1 | Macro F1 (mean of repeats) |
|---|---:|---:|---:|---:|
| Production | 0.669 | 0.718 | 0.693 | 0.8323 |
| Production + rescue | 0.620 | 0.727 | 0.669 | 0.8269 |

Flows moved to facebook over 10 repeats: 11 (true labels: instagram 8, google 1, x 1, facebook 1). Facebook flows fixed by
majority: 0; broken: 0. Mean detector P(fb) per facebook flow: `flow_000024` 0.55, `flow_000231` 0.11, `flow_000368` 0.38,
`flow_000610` 0.54, `flow_000617` 0.48, `flow_000799` 0.55, `flow_000809` 0.71, `flow_001145` 0.53, `flow_001168` 0.73,
`flow_001324` 0.23, `flow_001331` 0.27.

## Interpretation

The undersampling ensemble ranks facebook flows like production does: the flows production misses (`flow_000231`,
`flow_000368`) score low here too. Its extra facebook calls are mostly instagram flows (the shared Meta openings, 035).
Changing how often facebook is seen does not create information that separates it.

## Decision

Gate failed; stage 2 not run; no model change.
