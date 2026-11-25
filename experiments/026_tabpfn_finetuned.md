---
title: '026: Fine-tuned TabPFN v2 (Task 1)'
created: 2026-10-01
creator: sidhantbas
description: 'Does fine-tuning TabPFN on our flows (Charles: "TabFM needs fine-tuning") beat the zero-shot use in 024?'
experiment:
  id: '026'
  tasks:
  - task1
  lever: model
  status: unfinished
  verdict: 'Fine-tuned TabPFN: the seed-2028 confirmation was stopped by the user and never rerun'
---
# 026: Fine-tuned TabPFN v2 (Task 1)

- **Date:** 2026-10-01
- **Question:** Does fine-tuning TabPFN on our flows (Charles: "TabFM needs fine-tuning") beat the zero-shot use in 024?
- **Status:** **unfinished**: cv_seed 2028 confirmation was stopped by the user (all Python processes killed) and not rerun
- **Script:** `src/exp026_tabpfn_finetuned.py`; `models.tabpfn_ft`, `models.PlusMember` (classes_ fix for the fine-tuned wrapper)
- **Runs:** `results/*_026_*`

## Setup

`FinetunedTabPFNClassifier` (tabpfn 9.0.0), model v2, CPU, package defaults fixed in advance (≤ 30 epochs, lr 1e-5,
early stopping on an internal 10% split of the training fold). About 15 s per fit with 14 threads; early stopping
ended a test fit at epoch 8.

## Results (Task 1)

| Variant | cv_seed | Macro F1 | Δ vs champion | W / L / T |
|---|---|---|---|---|
| ft_alone | 2026 | 0.7695 | −0.037 | 16 / 34 / 0 (facebook −0.198) |
| ft_member (022 model + fine-tuned TabPFN, 1/3 weight, facebook kept) | 2026 | 0.8249 | +0.018 | 33 / 11 / 6, BETTER |
| ft_member | 2027 | 0.8236 | +0.018 | 37 / 11 / 2, BETTER |
| ft_member | 2028 | — | — | not run (stopped) |

Fine-tuned vs zero-shot (024) member at cv_seed 2026: Δ +0.001, 6 wins / 1 loss / 43 ties. Fine-tuning with the
package defaults barely changes TabPFN on 264 training flows; the zero-shot member failed its 2028 confirmation
(31/16), so 2028 decides this one too.

## Decision

Pending the 2028 confirmation.
