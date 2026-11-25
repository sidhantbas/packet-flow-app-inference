---
title: '032: Each app''s USP, and predicting from "probabilities of behaviour"'
created: 2026-10-01
creator: sidhantbas
description: Does each app have a distinctive packet-level signature, and does a likelihood model built on those levels
experiment:
  id: '032'
  tasks:
  - task1
  - task2
  lever: model
  status: rejected
  verdict: App signatures (instagram bursts AUC 0.91 ...) are real but moderate; naive Bayes on behaviour levels 0.64 / 0.53 alone, -0.040 / -0.007 as a member
---
# 032: Each app's USP, and predicting from "probabilities of behaviour"

- **Date:** 2026-10-01
- **Question:** Does each app have a distinctive packet-level signature, and does a likelihood model built on those levels
  predict well or add to the ensembles?
- **Status:** done; prediction variants rejected; USP profile kept for the report
- **Script:** `src/exp032_behaviour_nb.py`; `models.BehaviourNB`, `models.ProbaMix`. USP profile computed inline
  (one-vs-rest ROC AUC of each feature on the 330 labelled flows; 17 full-flow + 12 opening columns, no opening timing).

## USP per app (strongest one-vs-rest signals; AUC 0.5 = no signal)

| App | Signature | Strongest signals (AUC; app median vs others) |
|---|---|---|
| instagram (19) | many bursts, huge and long flows | burst_count 0.91 (35 vs 2); packets down 0.84 (329 vs 15); bytes up 0.84; duration 0.84 (235 s vs 14 s) |
| facebook (11) | opening receives more than it sends; more bursts | opening up/down bytes 0.20 (0.86 vs 3.4); opening packets up 0.24 (2 vs 3), down 0.76 (3 vs 2); burst_count 0.73 (6 vs 2) |
| google (131) | large opening packets both ways, UDP | opening mean size down 0.76 (889 B vs 74 B); opening bytes up 0.75; opening mean size up 0.73 (1363 vs 515 B); transport 0.72 |
| youtube (55) | large upstream packets all through the flow; balanced bytes | mean size up 0.80 (598 vs 221 B); opening bytes up 0.76; std size up 0.71; up/down bytes 0.70 (1.02 vs 0.63) |
| mozilla (41) | everything small | mean size up 0.15 (119 vs 312 B); opening bytes up 0.15 (493 vs 2659); opening mean size up 0.15; opening mean size down 0.18 |
| x (73) | TCP only, tiny opening | transport 0.17 (all TCP); opening bytes down 0.17 (140 vs 1656); opening mean size up 0.19 (265 vs 1330 B) |

Behavioural reading (interpretation, not measured): Instagram = scrolling feeds loading in waves; Facebook = background
notifications/keep-alives; Google = quick QUIC lookups; YouTube = player streaming and reporting playback; Mozilla = small
browser requests over TCP; X = timeline/API calls over TCP.

## Prediction from behaviour probabilities (settings fixed before running)

BehaviourNB: 5 quantile levels per feature (cut points fitted on the training fold), categorical naive Bayes, Laplace
smoothing 1, equal class priors. Member weight 1/3. cv_seed 2026, vs champions.

| Variant | Task 1 | Task 2 |
|---|---|---|
| nb_alone | 0.642 (-0.165, 1/49) | 0.531 (-0.224, 0/50) |
| nb_member | 0.767 (-0.040, 2/48) | 0.747 (-0.007, 4/33/13) |

## Interpretation

The signatures are real but, apart from Instagram's bursts, each is moderate (AUC 0.70-0.85), and several apps share the
same levels. Naive Bayes multiplies evidence from many strongly related columns (several are exact formulas of others), so
it double-counts; five coarse levels also discard the fine opening detail (exact packet sizes) that the trees use. A
likelihood-of-behaviour model is a good explanation tool, not a better predictor here.

## Decision

Reject both prediction variants. Keep the USP table for the technical report.
