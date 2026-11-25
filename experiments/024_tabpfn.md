---
title: '024: TabPFN v2'
created: 2026-09-30
creator: sidhantbas
description: Does TabPFN (a transformer pretrained on synthetic tables, built for small data) beat or improve the champions?
experiment:
  id: '024'
  tasks:
  - task1
  - task2
  lever: model
  status: inconclusive
  verdict: 'TabPFN v2: alone worse (Task 1 0.769, facebook -0.21; Task 2 0.734); as a 3rd Task 1 member +0.014 to +0.018 on 5 seeds but fails rule v2 on 2028/2029; pretrained, excluded'
---
# 024: TabPFN v2

- **Date:** 2026-09-30
- **Question:** Does TabPFN (a transformer pretrained on synthetic tables, built for small data) beat or improve the champions?
- **Status:** done; not adopted (fails confirmation by one seed)
- **Script:** `src/exp024_tabpfn.py`; `models.tabpfn`, `models.PlusMember`; the member runs were started inline
- **Runs:** `results/*_024_*`
- **Reference:** champions; confirmation seeds vs the 022 Task 1 model re-run in 023

## Setup and compliance

`tabpfn` 9.0.0 (Apache-2.0), model version **v2** (ungated weights, 29 MB, downloaded once to
`~/Library/Caches/tabpfn`), CPU, one thread per fold. The package has no telemetry; network use is the weight
download only; no data leaves the machine. Newer versions (v2.5+) are gated behind a browser license acceptance and
were not used. An outside pretrained model is "information beyond the released feature files": disclose if adopted.
The cloud client `tabpfn-client` (uploads data) must never be used.

## Results

TabPFN alone (cv_seed 2026): Task 1 0.769 (−0.038; facebook −0.213, other classes ≈ equal), Task 2 0.734 (−0.020).
A single-fold smoke test gave 0.941, which was luck.

TabPFN as a third member of the Task 1 model (`PlusMember`: 2/3 × 022 model + 1/3 × TabPFN; facebook kept):

| cv_seed | Macro F1 | Δ | W / L / T | Verdict |
|---|---|---|---|---|
| 2026 | 0.824 | +0.017 | 33 / 11 / 6 | BETTER (facebook +0.054, mozilla +0.035) |
| 2027 | 0.824 | +0.018 | 37 / … | BETTER |
| 2028 | 0.805 | +0.015 | 31 / 16 / 3 | NEAR-MISS (66%) |
| 2029 | 0.828 | +0.017 | 30 / 18 / 2 | NEAR-MISS (62%) |
| 2030 | 0.829 | +0.014 | 35 / … | BETTER |

## Decision

Not adopted: rule v2 needs a pass on cv_seeds 2027 **and** 2028. The gain is positive on all five split sets
(+0.014 to +0.018), so it stays the strongest open lead. It is not re-tested with tweaks (weight, estimators) against
the same seeds, which would be fishing.
