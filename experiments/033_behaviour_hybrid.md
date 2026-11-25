---
title: '033: Hybrid: production model + behaviour model as a gated Bayesian correction'
created: 2026-10-01
creator: sidhantbas
description: Can the behaviour model (032) improve the best pipelines (test 84.62) if it only corrects uncertain
experiment:
  id: '033'
  tasks:
  - task1
  - task2
  lever: decision
  status: rejected
  verdict: 'Gated behaviour hybrid (lambda, tau by nested CV): Task 1 -0.012, Task 2 -0.002; the inner selection picks up luck'
---
# 033: Hybrid: production model + behaviour model as a gated Bayesian correction

- **Date:** 2026-10-01
- **Question:** Can the behaviour model (032) improve the best pipelines (test 84.62) if it only corrects uncertain
  predictions and only where the training data says it helps?
- **Status:** done; rejected
- **Script:** `src/exp033_behaviour_hybrid.py`; `models.BehaviourHybrid`, `models._hybrid`, `models._decide`;
  `src/evaluation_metric.py` (the organisers' `_macro_f1`, imported unchanged)
- **Runs:** `results/*_033_*`

## Design (fixed before running)

p_final ∝ p_model × p_behaviour^λ on rows whose top-two margin of p_model is < τ (others unchanged), then the production
decision (Task 1: facebook override; Task 2: facebook/instagram stage). p_model = Task 1 blend probabilities / Task 2 base
SoftVote probabilities; p_behaviour = BehaviourNB (032). (λ, τ) chosen inside each outer training fold by a 3-fold inner
CV on official macro F1, from λ ∈ {0, 0.25, 0.5, 1} × τ ∈ {0.1, 0.2, 0.3}; λ = 0 ("no change") always available, ties to
the smaller λ. The chosen setting is applied once to the outer held-out fold. The test result (84.62) was not used.

## Results (cv_seed 2026, vs champions)

| Task | Macro F1 | Δ | W / L / T | Folds where the inner CV chose λ = 0 |
|---|---|---|---|---|
| 1 | 0.795 | -0.012 | 3 / 25 / 22 | 19 of 50 (λ = 0.25, τ = 0.1 in 16) |
| 2 | 0.752 | -0.002 | 3 / 8 / 39 | 21 of 50 (λ = 0.25, τ = 0.1 in 12) |

Task 1 per class: google +0.006, youtube -0.003, instagram -0.031, facebook -0.021, x -0.016.

## Interpretation

The inner CV saw small gains in about 60% of folds that did not transfer to the held-out rows: with ~176 flows per inner
fold (about 6 facebook), the selection itself is noisy and picks up luck. Consistent with 031: there is little room at
narrow margins, and the behaviour model's errors (double-counted, coarse evidence) are not complementary enough.

## Decision

Reject. No confirmation run (fails at 2026, as planned).
