---
title: "105: Reproducing Infralibre's FlowLens-v9-PairSwap (95.01), with due diligence on the claim"
created: 2026-10-13
creator: sidhantbas
description: "Frozen reproduction of the new leader's note (cross-view ensemble plus a count-preserving Task 1 consensus swap) and a due-diligence test of what the note can explain: how often a label-blind pair swap fixes both flows, compared with the exactly +2 correct flows their score change implies. Task 1; never-used seeds 2116-2120; components in src/flowkit/."
source:
  - ../docs/reports/leaderboard-method-reproduction.md
  - ../submissions/raw/leaderboard-final-test-2026-10-13-evening.txt
  - 102_flowlens_reproduction.md
  - 100_cross_task_meta_rescue.md
experiment:
  id: '105'
  tasks: [task1]
  lever: decision
  status: rejected
  verdict: 'Not reproduced: cross-view ensemble + count-preserving consensus swap is WORSE than production on 5 of 5 never-used seeds (-0.070); a blind swap breaks 2-3 correct flows per fixed one; their implied +2 flows came out of a blind swap in 1-2% of batches; on our test set the swap changes nothing'
---

# 105: Reproducing FlowLens-v9-PairSwap, with due diligence

**Status: done 2026-10-13. Protocol frozen (`f5975e2`) before any code or run.**
**Verdict: not reproduced; the swap breaks more flows than it fixes, and the +2 their score implies is a 1-2% outcome for a label-blind swap.** Results are below the protocol. Do not edit the frozen
sections after execution starts. Sid, 2026-10-13: "whatever they have put, it can not be totally real ... reproduce it ... but at
the same time due diligence it ... these scorers know that the trailers behind will be seeing it."

## The claim (verbatim, leaderboard 2026-10-13 evening)

> **FlowLens-v9-PairSwap** (Infralibre): Class-balanced cross-view ensemble with a count-preserving Task 1 consensus swap. Task
> 2 remains the validated prefix-five-only model with no Task 1 information used.

Total 95.01, up from 93.74 (v8, experiment 102). Task 2 unchanged (46.79). Task 1 46.94 → 48.21: macro F1 0.939 → 0.964,
accuracy 0.93 → 0.95, i.e. **75 → 77 correct of 81: exactly +2 flows.**

## Due diligence: what the note can and cannot be

A note on a public leaderboard is written for the organisers and for every team behind. It may be accurate, deliberately vague,
or a cover for leaderboard feedback (5 uploads a day on the set that ranks the competition). Checks fixed now:

| # | Question | How we answer it |
|---|---|---|
| D1 | Is +2 correct flows what one count-preserving pair swap gives? | Arithmetic above: one swap of two mutually mislabelled flows (a predicted as b, b predicted as a), both corrected, gives exactly +2 at constant class counts |
| D2 | How often does a label-blind consensus swap fix **both** of its flows? | Measured in CV: for every swap the rule makes, both fixed / one / none / both broken |
| D3 | How likely is the observed outcome (+2, nothing broken) for a team applying the rule blindly? | From D2: the probability that a swap set makes a net gain of 2 with no flow broken, per batch of about 81 flows |
| D4 | Could the cross-view ensemble alone explain it? | V0 against production in CV; V0 is what our Task 1 production already does in a richer form (022, 028, 089) |
| D5 | Is the Task 2 statement informative? | Task 2 is unchanged since v8 (102 reproduced it); the sentence is a compliance statement (condition 2), not a method |

If D2-D3 show that a blind swap rarely fixes both flows, the +2 is more consistent with leaderboard feedback or luck than with the
described method. We record this as a finding and never act on it.

## Reading of the method (unknown details fixed now)

| Part | Our implementation |
|---|---|
| Class-balanced cross-view ensemble | Mean probability of two balanced `SoftVote`s: view A on the 17 Task 1 columns, view B on the 12 no-timing first-5 columns (the Task 2 file, allowed for Task 1) |
| Consensus swap | Within a batch: flows labelled a whose other view says b, and flows labelled b whose other view says a, are swapped in pairs (a ↔ b), most confident first (the other view's probability), as many pairs as the smaller side allows. Class counts are unchanged by construction |
| Count-preserving | Relative to the labels before the swap; a measured-only variant first matches the batch's true counts |

## Frozen design (Task 1)

| Arm | Labels | Usable in a submission |
|---|---|:---:|
| P | Production `task1_cross_task` (100) | — |
| V0 | Cross-view ensemble, argmax | ✅ |
| V1 | V0 + consensus pair swap against view B | ✅ |
| V2 | Production + the same swap against the Task 2 production model's opening view (as 100's inner model), ranked by its SoftVote probability | ✅ |
| V3 | V0 matched to the held-out fold's true counts (simulated disclosure, as 102), then the swap | ❌ measurement only |

- **Folds:** repeated stratified 5 × 10 at cv_seeds **2116-2120** (0 runs in `results/`); model seed = fold index; each arm against P
  on the same folds.
- **Swap accounting (D2):** from the out-of-fold predictions, every flow changed by a swap (V1 vs V0, V2 vs P, V3 vs its
  matched base) is classed fixed, broken or wrong either way; swaps per fold and the share of swaps whose both flows were fixed.
- **Test-set effect (no labels):** V1 and V2 fitted on train + validation; number of swaps on the 81 test flows and the flows
  involved, against our submitted Task 1 file.
- **Smoke checks:** the swap preserves class counts exactly on random inputs; with identical views it makes no swap.

## Decision rule

- **Method reproduced on our data:** V1 or V3 is rule v2 BETTER than P on all five seeds.
- **Compliant candidate:** V0, V1 or V2 rule v2 BETTER than P on all five seeds, then proposed separately (user decision and the
  upload rule).
- **Due diligence:** D1-D5 reported as above, whatever the result.

## Boundaries

Train + validation labels only; "disclosed" counts are the held-out fold's own labels; the test `label_counts` are never read.
Task 1 may read the Task 2 file (as 022); Task 2 is not touched. No upload. Nothing here infers test labels.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-13 | Protocol frozen and committed | before any code or run |
| 2026-10-13 18:06 | Code committed (`96ace35`): `src/flowkit/swap.py`, runner; smoke checks | the swap preserves class counts and only moves flows to the other view's label; identical views make no swap |
| 18:06-18:12 | All arms × cv_seeds 2116-2120 (`--all`), including the V3M reference that the protocol's V3 accounting needs | 30 runs `…_105_<arm>_s<seed>`, no errors |
| after the runs | `--analyse`, `--test-effect` | `experiments/105_evidence/analysis.json`, `test_effect.json` |

No deviation from the frozen protocol (V3M is the matched base named in the swap accounting, recorded as a run so it is verifiable).

### Commands

```bash
.venv/bin/python src/exp105_pairswap_reproduction.py --smoke
.venv/bin/python src/exp105_pairswap_reproduction.py --all
.venv/bin/python src/exp105_pairswap_reproduction.py --analyse
.venv/bin/python src/exp105_pairswap_reproduction.py --test-effect
```

## Results

### Every arm against production (Task 1 CV macro F1, mean of five never-used seeds; P = 0.850)

| Arm | Macro F1 | Δ vs P | Verdict |
|---|---:|---:|---|
| V0 cross-view ensemble | 0.785 | −0.065 | WORSE ×5 |
| V1 + consensus pair swap (the method) | 0.780 | **−0.070** | WORSE ×5 |
| V2 production + the swap against our Task 2 view | 0.830 | −0.020 | WORSE ×5 |
| V3M V0 matched to the true counts (reference) | 0.796 | −0.054 | WORSE ×5 |
| V3 V3M + the swap (measured only) | 0.793 | −0.056 | WORSE ×5 |

### Due diligence: what a label-blind swap does (D2, D3; 250 folds of about 66 flows)

| Swap applied to | Flows changed | Fixed | Broken | Wrong either way | Folds with any swap | Folds with net +2 or more and nothing broken |
|---|---:|---:|---:|---:|---:|---:|
| V0 → V1 | 230 | 44 | **142** | 44 | 99 | **3 (1.2%)** |
| P → V2 | 366 | 70 | **236** | 60 | 126 | **3 (1.2%)** |
| V3M → V3 | 174 | 54 | **99** | 21 | 73 | **5 (2.0%)** |

**A consensus swap breaks about 2-3 correct flows for every one it fixes.** The outcome Infralibre's score change implies (D1:
exactly +2 correct flows at constant class counts) came out of a blind swap in 1-2% of batches.

### Effect on our test predictions (no labels)

| Arm | Changes vs our submitted Task 1 |
|---|---:|
| V0, V1 | 4 (identical: the swap finds no mutual pair on our test set) |
| V2 | **0** (no mutual disagreement pair between our production and our Task 2 view on the test set) |

## Verdict

- **Not reproduced on our data.** The method (V1) is WORSE than production on all five never-used seeds (−0.070); the swap
  itself lowers every base it is applied to. Status: rejected.
- **Due diligence:**
  - D1: their +2 correct flows at constant counts is exactly what one perfect pair swap gives.
  - D2: a label-blind consensus swap is wrong far more often than right: 2-3 broken per fixed flow on every base.
  - D3: the observed outcome occurs in about 1-2% of batches under the blind rule.
  - D4: the cross-view ensemble alone is 0.065 below our production, which already combines the views.
  - D5: the Task 2 sentence repeats a compliance statement and describes nothing new.
  - **Reading:** the note does not describe a mechanism that produces +2 reliably. The jump is more consistent with a lucky draw
    or with choosing the swapped pair by leaderboard feedback (5 uploads a day on the ranking set). We record this as a finding
    about the note, not about the team, and never act on it.
- **Nothing to adopt:** on our own test predictions the swap would change nothing (V2: 0 changes).
