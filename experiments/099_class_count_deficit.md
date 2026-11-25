---
title: "099: Are some classes under-predicted on the test set, and would a count-aware rescue be worth a submission?"
created: 2026-10-12
creator: sidhantbas
description: "Measurement: compares production's predicted test class counts with the counts implied by the stratified split design, measures in cross-validation how often such deficits occur and how precise a count-aware rescue of the under-predicted class would be, and decides whether a candidate experiment is justified. No test labels, no metadata label_counts."
source:
  - 095_disclosed_count_simulation.md
  - 043_topk_facebook.md
  - 098_facebook_audit_and_final_candidate.md
experiment:
  id: '099'
  tasks: [task1, task2]
  lever: decision
  status: measured
  verdict: 'Task 1 predicts 2 instagram test flows vs about 5 expected (a deficit never seen in 50 CV folds); a count-aware rescue is not justified (flips right 27% / 14%, delta < 0); post hoc: Task 2 instagram + Task 1 non-Meta means Meta 96% of the time'
---

# 099: Class-count deficits on the test set

**Status: done 2026-10-12. Protocol frozen (`a62611e`) before analyses A-E.**
**Verdict: the Task 1 instagram deficit on the test set is real and unusual; a count-aware rescue is not justified; one sharper cross-task signal goes to experiment 100.** Results are below. User 2026-10-12: "based on our experiments what is the next insight ... the main goal is closing the F1 score ... find a
useful way to make more bold submissions."

## Observation that motivates it (already known before freezing)

The final candidate (`submissions/final-2026-10-12-089-014/`, identical to the ranked entry) predicts, on the 81 test flows:
Task 1 instagram 2 and facebook 3; Task 2 instagram 4, facebook 2, x 24, mozilla 7. The released split is stratified 60/20/20
(`metadata.json`: `split_fractions`, `split_seed`; the test `label_counts` are **not** read), so each class's test count should be
close to its validation count (google 33, x 18, youtube 14, mozilla 10, instagram 5, facebook 3, on 83 flows).

## Frozen analyses

**A. Expected vs predicted counts.** Expected test count per class: validation count × 81 / 83 and training share × 81 (two
estimates; both derived from labelled splits and the documented split design only). Reported next to each task's predicted counts.

**B. How unusual is the deficit?** In the production out-of-fold predictions (Task 1: 089, `experiments/098_evidence/trace_all.csv`,
cv_seed 2026; Task 2: 014, refitted on the same folds as a diagnostic), per held-out fold: predicted count − true count per class,
scaled to 81 flows. Reported: the distribution, and the share of folds with an instagram deficit at least as large as the test's
(scaled), and the same for Task 2 x surplus and mozilla deficit.

**C. Calibration of the rescue score.** Instagram score s_ig: Task 1 = mean of the three experts' instagram probabilities (whole-flow,
opening, rest-of-flow; as traced in 098); Task 2 = the 014 base SoftVote's instagram probability. Among held-out flows production
does **not** call instagram: the share that is truly instagram among the top-1, top-2 and top-3 per fold by s_ig, and by s_ig bins.

**D. Count-aware rescue rule (fixed now).** In each held-out fold, k = max(0, E − predicted instagram count) with E = round(n_fold ×
instagram share of the training fold); relabel the k non-instagram flows with the highest s_ig as instagram. Reported per task: flips
made, flips correct, paired Δ macro F1 per fold (wins / losses / ties), instagram precision and recall before and after. As a
headroom bound only: the same with E = the fold's true instagram count (an oracle, not a usable rule).

**E. Test application (no labels).** The k that rule D would apply on the test set and the flows it would relabel (flow id, current
label, s_ig), for each task.

## Decision rule (fixed now)

A candidate experiment for a "bold" submission is justified only if, in D (non-oracle), flips are correct at least 50% of the time
and the paired Δ macro F1 is > 0. Then it gets its own frozen experiment on never-used seeds (rule v2 on all five) before any upload.
Otherwise the deficit is reported as a finding that our probabilities cannot act on. Production is not changed here.

## Boundaries

Train + validation labels only; test features only for predictions; no test labels or `label_counts`; Task 2 analyses use only Task 2
files; no capture time or order.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-12 | Protocol frozen and committed | before analyses A-E |
| 2026-10-12 | Analysis script committed and run | `src/exp099_count_deficit.py`; `experiments/099_evidence/analysis.json`, `test_scores_*.csv`; the Task 2 refit reproduces the 014 champion's predictions exactly |
| 2026-10-12 | Post-hoc measurement, **not part of the frozen protocol** | who is right when Task 1 and Task 2 disagree about Meta (saved predictions, seeds 2026-2028), prompted by analysis E |

No deviation from the frozen protocol for A-E.

## Results

### A. Expected vs predicted test counts

| Class | Expected (validation × 81/83) | Expected (training share × 81) | Task 1 predicted | Task 2 predicted |
|---|---:|---:|---:|---:|
| facebook | 2.9 | 2.7 | 3 | 2 |
| google | 32.2 | 32.2 | 33 | 32 |
| **instagram** | 4.9 | 4.7 | **2** | 4 |
| mozilla | 9.8 | 10.1 | 9 | **7** |
| **x** | 17.6 | 17.9 | 20 | **24** |
| youtube | 13.7 | 13.5 | 14 | 12 |

### B. How unusual are these deviations? (per held-out fold, scaled to 81 flows; seed 2026)

| | Mean | SD | 5th-95th percentile | Test |
|---|---:|---:|---|---:|
| Task 1 instagram (predicted − true) | −0.64 | 1.45 | −2.45 to +1.90 | about −3 |
| Task 2 x | +2.14 | 1.98 | −1.23 to +4.91 | about +6 |
| Task 2 mozilla | −0.93 | 1.76 | −3.68 to +1.90 | about −3 |

**A Task 1 instagram deficit of 3 or more per 81 flows occurred in 0 of 50 folds.** Task 1 under-predicts instagram in CV too
(precision 0.848, recall 0.732), but the test deficit is beyond its usual range. Task 2's x surplus is beyond its 95th percentile;
its mozilla deficit is within range.

### C. Calibration of the instagram score among flows not called instagram

| | Task 1 | Task 2 |
|---|---:|---:|
| Truly instagram among the top-1 per fold | 0.16 | 0.12 |
| top-2 | 0.16 | 0.08 |
| top-3 | 0.14 | 0.053 |

Task 1 score bins (truly-instagram rate): 0.10-0.20 → 0.163 (104 flows), 0.20-0.30 → 0.114 (35), 0.30-0.50 → 0.113 (53),
≥ 0.50 → 0.333 (9). The instagram score of a flow production did not call instagram is a weak signal.

### D. Count-aware rescue

| | Task 1 rule | Task 1 oracle count | Task 2 rule | Task 2 oracle count |
|---|---|---|---|---|
| Flips (correct) | 44 (12) | 37 (12) | 28 (4) | 23 (4) |
| Flip precision | **0.27** | 0.32 | **0.14** | 0.17 |
| Δ macro F1 per fold | **−0.0169** | −0.0140 | **−0.0015** | 0.0000 |
| Folds won / lost / tied | 7 / 20 / 23 | 7 / 16 / 27 | 4 / 10 / 36 | 4 / 8 / 38 |
| Instagram precision, recall (before → after) | 0.848, 0.732 → 0.726, 0.795 | → 0.751, 0.795 | 0.711, 0.753 → 0.642, 0.774 | → 0.656, 0.774 |

### E. What the rule would do on the test set

Task 1: E = 5, predicted 2, k = 3: `flow_000223` (youtube, s_ig 0.427), `flow_001187` (facebook, 0.292), `flow_001003` (google,
0.184). Task 2: k = 1: `flow_000007` (youtube, s_ig 0.024). Task 1's current instagram calls are confident (0.847, 0.995).

### Post-hoc measurement: who is right when Task 1 and Task 2 disagree about Meta

Not in the frozen protocol; prompted by E, where the two Task 1 test flows with the highest instagram score are exactly the two
test flows Task 2 calls instagram and Task 1 does not. Saved out-of-fold predictions, seeds 2026-2028 (089 vs 014 on the same
folds), pooled over 30 repeats:

| Case | Cases | Task 1 right | Task 2 right | Truth |
|---|---:|---:|---:|---|
| Task 2 instagram, Task 1 facebook | 124 | **90** | 33 | facebook 90, instagram 33 |
| **Task 2 instagram, Task 1 non-Meta** | 52 | **1** | 18 | **facebook 32, instagram 18**, google 2 |
| Task 2 facebook, Task 1 not facebook | 71 | **56** | 12 | |
| All disagreements | 978 | 631 | 194 | |

The useful case rests on 11 distinct flows, 9 of them Meta (facebook 001145, 000809, 001168, 001331, 000799; instagram 000477,
000210, 000359, 000215) and 2 google flows once each. When Task 2 says facebook and Task 1 says non-Meta, the cases come mostly from
two non-Meta flows (000559 google, 000535 x): not useful. On the test set the two tasks disagree on 7 flows; exactly one is in the
useful case: `flow_000223` (Task 1 youtube, Task 2 instagram).

## Verdict

- **The deficit is real and unusual** (0 of 50 CV folds), so Task 1's instagram recall is the most likely large loss on the test
  set: if the test holds about 5 instagram flows and both current calls are right, instagram F1 is about 0.57, which alone costs
  about 0.07 macro F1 (about 3.6 points).
- **A count-aware rescue is not justified** (frozen rule: flips right 27% and 14% of the time, Δ < 0 in both tasks, even with oracle
  counts). The instagram score of a flow production did not call instagram is too weak to choose the right flows.
- **One defensible, sharper signal** came out of the post-hoc look: when the opening-only Task 2 model says instagram but Task 1
  says a non-Meta app, the flow is Meta 96% of the time. Because it was found after looking, it is tested as its own frozen
  experiment (100) on never-used seeds before it can be used.
