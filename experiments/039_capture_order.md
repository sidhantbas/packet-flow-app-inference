---
title: '039: Capture-order leakage (measurement only)'
created: 2026-10-05
creator: sidhantbas
experiment:
  id: 039
  tasks:
  - task1
  - task2
  lever: diagnostic
  status: measured
  verdict: Capture order follows start_rel exactly; 78% same-app runs vs 42.5% random, but kNN on order scores 0.50 and costs production -0.040; treated as off-limits
---
# 039: Capture-order leakage (measurement only)

- **Date:** 2026-10-05
- **Command:** `.venv/bin/python src/exp039_capture_order.py` (about 20 s); random-order baseline for part 2 run inline.
- **Production and submission unchanged.** Nothing here is logged as a candidate.

## 1. kNN on capture order, normal CV (cv_seed 2026)

| Ordering | k = 1 macro / facebook | k = 3 | k = 5 |
|---|---|---|---|
| flow_id number | 0.500 / 0.161 | 0.451 / 0.140 | 0.389 / 0.037 |
| start_rel | 0.508 / 0.155 | 0.475 / 0.176 | 0.421 / 0.000 |

flow_id order equals start_rel order (Spearman 1.000): flow_ids were assigned in capture order.

## 2. Same-app runs (330 labelled flows in capture order)

78% of labelled flows (259 of 330) sit in runs of two or more consecutive same-app flows; a random order gives 42.5% (95% range
36-49%). Mean run length: x 3.7 (longest 15), google 2.5 (10), mozilla 2.3 (9), instagram 1.6 (3), youtube 1.5 (3),
facebook 1.2 (2); only 4 of 11 facebook flows sit in a run.

## 3. Production + capture-order kNN (fixed design: 0.5 x production probabilities + 0.5 x 5-NN vote shares on start_rel, then the
production rules)

| Task | Production | Combined | Δ | Folds won / lost | facebook |
|---|---|---|---|---|---|
| 1 | 0.8277 | 0.7880 | -0.0397 | 11 / 39 | 0.674 -> 0.611 |
| 2 | 0.7544 | 0.7391 | -0.0153 | 16 / 34 | 0.410 -> 0.375 |

Estimated leaderboard (84.62 + 50 x CV change per task): **81.87**, below the current 84.62.

## 4. Rule text (verbatim)

- Challenge description: "The task is to build an AI/ML method that estimates the application associated with each communication
  flow using only statistical packet-flow features." / "Leakage Control: Direct identifiers and payload contents are removed." /
  "The challenge emphasizes practical deployment in real networks, not only classification accuracy. Important perspectives include
  early identification from the first few packets, robustness under class imbalance, lightweight model design, overfitting
  prevention, and clear handling of uncertain predictions."
- Conditions: "Participants must not attempt to recover direct identifiers such as DNS names, TLS SNI, HTTP Host values, IP
  addresses, URLs, domain strings, or payload contents." / "If information other than the provided feature files is used, it must
  be clearly described in the submitted technical report."
- Terms: "Participants must not use private labels or recover prohibited direct identifiers for prediction."

No text mentions flow_id order, start_rel, timestamps or capture-order leakage. flow_id and start_rel are not the "direct
identifiers" listed, and start_rel is in the provided files. **Ambiguous**: not explicitly banned, but using the capture position
contradicts "only statistical packet-flow features" and the deployment emphasis, and organisers inspecting code could reject it.

## Conclusion

Capture order carries real session structure (78% vs 42.5% in runs), but it does not help: alone it scores 0.50, it misses Facebook
(mostly isolated flows), and combined with production it costs 0.04 on Task 1. It does not plausibly explain the leader's 0.94.
