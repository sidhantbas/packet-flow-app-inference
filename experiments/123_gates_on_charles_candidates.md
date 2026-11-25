---
title: "123: Do Charles's 364 process-supported capture candidates pass our capture gates?"
created: 2026-10-20
creator: sidhantbas
description: "Frozen run of capture gates 1 and 2 (src/capture_checks.py, unchanged: nearest-neighbour proximity and adversarial-domain AUC fitted on the original train + validation flows) on Charles's 364 provisional capture candidates from his Charles 003 package, both extraction profiles, per group and combined, with a pre-registered adversarial AUC per feature family."
source:
  - 121_gates_on_clean_captures.md
  - 122_capture_handoff_deliverables.md
experiment:
  id: '123'
  tasks: [task1]
  lever: data
  status: measured
  verdict: 'Charles''s 364 candidates fail gate 2 in every scope and both profiles (adversarial AUC 0.965 all, 0.95-0.99 per group; same-label 5-NN facebook 0.02 vs 0.16, instagram 0.15 vs 0.41, youtube 0.32 vs 0.59); gate 1 passes; sizes and counts alone separate them (AUC 0.937), timing alone 0.932, min_iat 0.61. A stricter, independently extracted subset is no closer than ours (121); capture training stays closed'
---

# 123: Capture gates on Charles's 364 candidates

**Status: done 2026-10-20. Protocol frozen (`c1ba9c3`) before any code or run.**
**Verdict: Charles's subset fails gate 2 exactly as our clean extraction did; capture training stays closed.** Results are below
the protocol. Do not edit the frozen sections after execution starts.
Sid, 2026-10-20: finish Charles's 20 October handoff. His TODO leaves one item to Sid: "inspect the new subset's
class/protocol/session shifts; train-fitted nearest-neighbour and adversarial-domain diagnostics remain unrun". **Measurement only:**
no training, no model change, no test data.

## Question

Charles built his own 364-flow candidate subset of our captures (49 facebook, 157 instagram, 158 youtube; every packet from the
target app's process, inside the session's action window). 121 found that our clean extraction fails gate 2 (adversarial AUC
0.945). Does his stricter subset, with his independent extraction, fail the same way?

## Frozen design

**Inputs** (read with `git show d3189ba:<path>`, nothing copied into this repository except results):
`experiments/charles-003-capture-audit/evidence/20261020-flow-aggregates/<profile>/candidate_task1_features.csv`,
`candidate_task2_features.csv` and `candidate_labels.csv`, for the two profiles `observed` and `split-mtu1514-sensitivity`.
The group is the flow ID's first component.

**Originals:** train + validation features and labels of both tasks (330 flows, `cv.load_task`), as in 121.

**Gates:** `gate1`, `opening_report` and `gate2` from `src/capture_checks.py`, called unchanged (same columns, log1p scaling on the
originals, thresholds: per app, median nearest-neighbour distance ≤ the originals' 90th percentile and same-label 5-NN share ≥
the originals'; adversarial AUC ≤ 0.70 with at least 30 captured flows; RF 300 trees, 5-fold, seed 0).

**Scopes:** each profile on all candidates, on the iPhone pilot group and on the iPhone long group (Android has no candidates).

**Pre-registered family AUC** (the post-hoc analysis of 121, now fixed in advance): the same adversarial set-up (log1p,
standardised on the originals, RF 300 trees, balanced, 5-fold stratified, seed 0), observed profile, all candidates, on four column
sets of the 17 Task 1 statistics (`transport` as 0/1): **all 17**; **sizes and counts** (17 minus the six timing columns);
**timing** (`duration`, `mean_iat`, `std_iat`, `min_iat`, `max_iat`, `burst_count`); **`min_iat` alone**.

## Decision rule

- **If either profile passes gates 1 and 2 on all candidates,** a capture training test may follow under its own frozen protocol and
  the user's decision (Task 1 only).
- **If both fail gate 2,** the subset is no closer to the challenge data than our clean extraction; capture training stays closed.
  The family AUCs say where the difference sits (sizes/counts vs timing).

## Boundaries

Train + validation of the original data only; no test data; captures are compared, never trained on. Charles's files are read, not
modified; his labels are used as given (provisional).

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-20 | Protocol frozen and committed (`c1ba9c3`) | before any code change or run |
| 2026-10-20 | `src/exp123_gates_charles_candidates.py` run (19 s) | `123_evidence/gates_<profile>_<scope>.txt`, `family_auc.json`, `summary.json` |

No deviation from the frozen protocol.

## Results

Per-app cells: median distance to the nearest original flow / same-label share among the 5 nearest original flows (thresholds:
distance 90th percentile facebook 2.15, instagram 2.01, youtube 1.25; same-label share 0.16, 0.41, 0.59).
[`summary.json`](123_evidence/summary.json)

| Profile / scope | Flows | Gate 1 | Gate 2 | Adversarial AUC (≤ 0.70) | facebook | instagram | youtube |
|---|---:|---|---|---:|---|---|---|
| observed / all | 364 | PASS | **FAIL** | 0.965 | 1.99 / 0.02 | 2.08 / 0.15 | 1.12 / 0.32 |
| observed / iPhone pilot | 216 | PASS | **FAIL** | 0.988 | 2.01 / 0.02 | 2.11 / 0.13 | 0.78 / 0.39 |
| observed / iPhone long | 148 | PASS | **FAIL** | 0.963 | 1.97 / 0.03 | 1.55 / 0.30 | 1.19 / 0.28 |
| split-mtu1514 / all | 364 | PASS | **FAIL** | 0.961 | 1.99 / 0.02 | 2.08 / 0.15 | 1.10 / 0.33 |
| split-mtu1514 / iPhone pilot | 216 | PASS | **FAIL** | 0.988 | 2.01 / 0.02 | 2.11 / 0.13 | 0.78 / 0.39 |
| split-mtu1514 / iPhone long | 148 | PASS | **FAIL** | 0.950 | 1.89 / 0.03 | 1.55 / 0.30 | 1.19 / 0.30 |

**Family AUC** (observed, all 364; [`family_auc.json`](123_evidence/family_auc.json)): all 17 columns **0.969**; sizes and counts
without timing **0.937**; timing only **0.932**; `min_iat` alone **0.610** (`min_iat` = 0 in 76% of candidates vs 98% of originals).

**Label discovery** (nearest original flow's label): facebook candidates → google 21, youtube 10, instagram 9, x 5, **facebook 3**;
instagram → google 72, x 41, youtube 20, **instagram 12**; youtube → google 76, **youtube 39**, x 27.

## Verdict

**Charles's 364 candidates fail gate 2 in every scope and in both extraction profiles; capture training stays closed.**

1. **A stricter, independently extracted subset is no closer.** Every packet from the app's process (his rule) gives AUC 0.965,
   against 0.945 for our clean extraction (121) and 0.947 for the first extraction. The labels were not the problem: they agree
   with ours on all 364 flows (122).
2. **The difference sits in sizes and counts as much as in timing** (0.937 vs 0.932), so it cannot be explained by timestamp
   resolution (`min_iat` 0.610) or by the merged-segment handling (the MTU-split profile changes the AUC by at most 0.013).
3. **The captured Meta flows look like google flows to the original data:** only 3 of 49 facebook and 12 of 157 instagram
   candidates have a nearest original flow of their own app. Training on them would teach the model the wrong shapes (056: facebook
   −0.30 to −0.38).

This answers Charles's open item ("train-fitted nearest-neighbour and adversarial-domain diagnostics remain undone"): done, both
fitted on the original train + validation flows, and the subset fails them.
