---
title: "098: Facebook error audit of production 089, candidate decision, and final submission preparation"
created: 2026-10-12
creator: sidhantbas
description: Stage-by-stage diagnostic trace of production Task 1 (089) for every facebook flow and every false facebook call, the decision that no candidate experiment is justified, and the preparation of the final submission artifact (089 + 014).
source:
  - 097_reliability_089_vs_084.md
  - 034_meta_gate.md
  - 035_h1_checks.md
  - ../reports/evidence-handoff/README.md
experiment:
  id: 098
  tasks:
  - task1
  lever: diagnostic
  status: measured
  verdict: 'Facebook audit: 22 of 31 facebook errors have every expert wrong; no candidate justified; final file identical to the ranked entry'
---

# 098: Facebook audit, candidate decision and final submission preparation

**Status: done 2026-10-12.** User brief 2026-10-12 (pasted): audit facebook errors, run at most one justified candidate, prepare
the strongest defensible submission. **Verdict: no defensible candidate; the final artifact is 089 + 014, identical to the current
production file.**

## Stage 1: audit (diagnostic computation, not a candidate experiment)

Stage-level predictions were not saved, so the frozen production pipeline (`models.task1_bundle`) was refitted on the original
training folds of its champion run (`20261010T004051Z_089_production_check_s2026`, cv_seed 2026, 5 × 10), tracing every stage for
every held-out flow (`src/exp098_facebook_audit.py`). **The traced final labels equal the saved out-of-fold predictions for all
3,300 held-out predictions.** Twin-aware evidence comes from the 097 grouped run of 089 (`20261011T230759Z_097_V089_grouped_s2026`).
Evidence: `experiments/098_evidence/` (`trace.csv`, `trace_all.csv`, `flows.csv`, `summary.json`).

Stages traced: experts (whole-flow, opening, rest-of-flow) → averaged probabilities → Meta gate (with the whole-flow expert's
facebook-vs-instagram choice) → whole-flow Meta override → 17-column facebook keep → instagram revert → pair verifiers →
exact-opening override (final).

### Per facebook flow (10 held-out appearances each)

| Flow | Final predictions | Errors | Competing label | Opening match | Whole-flow near-twin in training | Whole / opening / rest expert (majority) | Twin-aware accuracy |
|---|---|---:|---|---:|---:|---|---:|
| flow_000024 | facebook 10 | 0 | — | 0.0 | 0.0 | facebook / facebook / facebook | 1.0 |
| flow_000231 | x 6, instagram 4 | 10 | x | 0.0 | 0.0 | instagram, youtube / x / x | 0.0 |
| flow_000368 | facebook 5, instagram 5 | 5 | instagram | 0.6 | 0.0 | facebook 5, instagram 5 / instagram / facebook 9 | 0.4 |
| flow_000610 | facebook 10 | 0 | — | 0.8 | 0.0 | facebook / facebook 8 / facebook | 0.8 |
| flow_000617 | facebook 8, instagram 2 | 2 | instagram | 0.9 | 0.0 | facebook 8 / instagram / facebook 9 | 0.5 |
| flow_000799 | facebook 9, google 1 | 1 | google | 0.0 | 0.0 | google 7 / instagram / youtube | 1.0 |
| flow_000809 | facebook 8, google 2 | 2 | google | 0.0 | **0.8** | facebook 8 / facebook 8 / facebook 8 | **0.0** |
| flow_001145 | facebook 5, google 4, instagram 1 | 5 | google | 0.0 | 0.0 | google 9 / instagram 6 / google 9 | 0.0 |
| flow_001168 | facebook 8, instagram 1, google 1 | 2 | instagram | 0.0 | **0.8** | facebook 8 / facebook 8 / facebook 8 | **0.0** |
| flow_001324 | facebook 7, mozilla 2, x 1 | 3 | mozilla | 0.8 | 0.0 | facebook 5, x 5 / facebook 8 / mozilla 6 | 0.7 |
| flow_001331 | facebook 9, google 1 | 1 | google | 1.0 | 0.0 | facebook 8 / instagram / youtube 5, google 5 | 0.8 |

Stage that first changes correctness (facebook appearances): the decision logic **adds** facebook recall. The share of facebook
appearances labelled facebook rises from 0.445 after averaging to 0.582 after the Meta gate and 0.718 after the whole-flow Meta
override; later stages change nothing for facebook. Expert accuracy on facebook: whole-flow 0.591, rest-of-flow 0.491, opening 0.418.

### False facebook calls (40 held-out predictions)

| True label | Predictions | Main flows |
|---|---:|---|
| instagram | 27 | flow_000379 (10/10), flow_001185 (10/10); five others once or twice |
| google | 10 | flow_000120 (4), flow_000559 (3), flow_000239 (2), flow_001398 (1) |
| youtube, x | 3 | flow_000229 (2), flow_000535 (1) |

flow_000379 and flow_001185 are the cross-label partners of facebook flows found in 035 (000368 ↔ 000379; 000809/001168 ↔ 001185):
all three experts call them facebook.

### Aggregate breakdown

| Category | Facebook errors (31) | False facebook calls (40) |
|---|---:|---:|
| A. Correct expert evidence lost by the decision logic (an intermediate stage was right) | 3 | 8 |
| B. Experts disagree and production selects incorrectly (an expert right, no stage right) | 6 | 6 |
| C. All three experts wrong | **22** | **26** |
| D. Success depends strongly on a training twin | flow_000809 and flow_001168 (each other's near-twins): right 8/10 on ordinary folds, **0/10 on twin-aware folds** | — |

Facebook accuracy is 1.00 when a whole-flow near-twin is in the training fold and 0.67 otherwise; 0.81 with an exact opening match
and 0.67 without. An oracle choosing the right expert measures headroom only; it is not an achievable model.

## Stage 2: is one experiment justified?

The only recurring-looking mechanism in A/B is the facebook-vs-instagram choice inside Meta, which production leaves to the
whole-flow expert while the rest-of-flow expert is right for flow_000368 (9/10) and flow_000617 (9/10). Checked on **all** 258
held-out predictions that are Meta in truth and in production (166 instagram, 92 facebook):

| facebook-vs-instagram choice by | Correct | facebook recall | instagram recall |
|---|---:|---:|---:|
| production (whole-flow expert + rules) | **0.845** | — | — |
| whole-flow expert alone | 0.822 | 0.783 | 0.843 |
| rest-of-flow expert alone | 0.779 | 0.717 | 0.813 |
| whole-flow + rest-of-flow average | 0.841 | 0.837 | 0.843 |

Where the two experts disagree, the rest-of-flow expert is wrong 23 times and right 12 times, and its wins come from three or four
flows. No rule that uses only permitted features or model outputs separates those flows from the ones it would break; the rest of
the error is category C (all experts wrong) or twin-dependent (D), which no decision stage can reach.

**Decision: no defensible candidate. No candidate experiment was run.** Production 089 + 014 is retained.

## Stage 4: final submission preparation

See the artifact folder `submissions/final-2026-10-12-089-014/` (README, configuration, hashes, validation) and the results
below.

### Stage 4 results

Built by `src/make_final_candidate.py` into [`submissions/final-2026-10-12-089-014/`](../submissions/final-2026-10-12-089-014/README.md)
(production artifacts untouched).

- **Validation:** all checks pass (81/81 IDs per task, each once, equal to the test features and the sample submission; 0 missing,
  0 extra; only the six labels; no forbidden columns; Task 2 reads only its own folder; official loader accepts JSON and ZIP;
  pipeline code reads no `metadata.json` / `label_counts`; rebuild byte-identical). A first run flagged the label-count scan
  because the checker script named those strings itself; the scan was restricted to the pipeline files and rerun.
- **Differences:** byte-identical to `production-089-bundle/` (upload 7, 87.24): **0 changes**, so another upload offers no score
  change. Versus `best-88.11-production-084/`: 2 Task 1 changes (`flow_000095` google → youtube, `flow_000906` youtube → google).
- **Platform:** format, coverage rules and total-score ranking verified from the official templates; deadline documented
  inconsistently (23 vs 24 October 2026, no timezone); upload allowance, best-vs-latest ranking and eligibility of earlier uploads
  unverified.
- **Recommendation:** retain the existing submission; resolve which upload the platform ranks before any further action.
