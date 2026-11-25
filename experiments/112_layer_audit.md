---
title: "112: Does every layer of the production pipeline still earn its place? (leave-one-layer-out audit)"
created: 2026-10-18
creator: sidhantbas
description: "Frozen leave-one-layer-out audit of production Task 1 (100 FB: 022 whole-run expert + 028 opening expert + 034 Meta gate + 065 rest-of-flow expert + 087 instagram rule + 084 verifiers + 036 exact-opening rule + 100 cross-task rescue) and Task 2 (014), on never-used seeds 2151-2155, with a pre-registered simplification follow-up (113)."
source:
  - 097_reliability_089_vs_084.md
  - 100_cross_task_meta_rescue.md
  - 110_task1_rescue_with_109b.md
  - 111_task1_learned_rescue_stacker.md
experiment:
  id: '112'
  tasks: [task1, task2]
  lever: hierarchy
  status: measured
  verdict: 'Every layer earns its place except the 034 Meta gate: removing it is Δ > 0 on 5 of 5 seeds (+0.0046; 46 W / 2 L / 204 T; 37 fixed, 1 broken; facebook +0.024) but BETTER on only 2 of 5 (too few changed folds), so not a candidate by the frozen rule; 0 test changes, so 113 not run; production stands'
---

# 112: Leave-one-layer-out audit of the production pipeline

**Status: done 2026-10-18. Protocol frozen (`e4bb8e5`) before any code or run.**
**Verdict: production is the best combination of its parts for the test set. Seven of eight layers earn their place; the 034 Meta
gate has become redundant (its removal helps in every seed, without changing a test prediction). 113 is not triggered.** Results
are below the protocol.
Do not edit the frozen sections after execution starts. Sid, 2026-10-18: the order of our decisions may have left layers that
only patch other layers ("go ahead and run 112"; then "run all with the goal of chasing … the highest score … we can").

## Question and evidence

- Production Task 1 was built one layer at a time, each adopted against the champion of its day (028 → 034 → 084 → 089 → 100).
  Later layers can be fitted to earlier layers' habits (110: the 100 rescue works *because of* 014's confusion).
- 097 audited 089's three additions on cv_seeds 2026-2028: the 036 rule and the 065 expert earned their place; the 087 rule was
  weakest (removal −0.003 / −0.002 / **+0.001**).
- **Question:** with all layers in place, which ones still add to macro F1, and does removing any of them *raise* it?

## Frozen design

**Task 1.** A configurable rebuild of `models.task1_cross_task` (the 34 production columns), identical to production when no layer
is dropped (checked in the smoke test). Each arm drops exactly one layer and keeps every other step unchanged:

| Arm | Layer dropped | What the pipeline does instead |
|---|---|---|
| P | none | production `models.task1_cross_task` (reference) |
| −028 | opening expert | two clerks = whole-run expert alone; gate average without the opening expert |
| −034 | Meta gate | no gate re-weighting (and no gate-chosen facebook/instagram step); argmax of the experts' average |
| −065 | rest-of-flow expert | gate average of the whole-run and opening experts only (034's average) |
| −087 | instagram rule | gate's instagram calls kept even where the two clerks say non-Meta |
| −084 | pair verifiers | no google-vs-instagram / google-vs-x re-decision |
| −036 | exact-opening rule | no exact-opening override |
| −100 | cross-task rescue | the 089 bundle alone |

The 022 whole-run expert (and its keep-facebook rule) is the base every other layer refers to, so it is not dropped.

**Task 2.** P2 = production `models.task2_model` (014); −014 = its 6-app balanced SoftVote alone (no facebook/instagram
specialist).

- Nothing is tuned. **Folds:** repeated stratified 5 × 10 on cv_seeds **2151-2155** (0 runs in `results/`); model seed = fold
  index. Each arm is compared with P (P2) on the same folds (`runlog`, rule v2).
- **Smoke check (one fold):** the rebuild with no layer dropped equals `models.task1_cross_task` exactly; each drop's changed
  predictions are counted.
- **Reported per layer:** paired Δ (arm − P) per seed with rule v2 verdict, per-class Δ, flows fixed / broken; test-set effect:
  Task 1 (Task 2) test predictions each arm would change against the submitted production file (no test labels exist or are
  read).

## Decision rule (fixed now)

| Result for a layer | Reading |
|---|---|
| Removal Δ < 0 on at least 4 of 5 seeds | the layer earns its place |
| Removal mostly tied, mean \|Δ\| < 0.002 | dead weight (kept: removing it changes nothing) |
| Removal rule v2 **BETTER on all 5 seeds** | the layer now hurts: a simplification candidate |
| anything else | inconclusive |

**Follow-up 113 (pre-registered):** if one or more layers are simplification candidates, experiment 113 tests production with all
of them removed together, on never-used cv_seeds 2156-2160, against P; it counts only if rule v2 BETTER on all five. A pass is a
production candidate (user decision) and an upload candidate only under the upload rule (at least 3 test predictions different
from every earlier upload). If no layer is a candidate, production stands and 113 is not run.

## Boundaries

Task 2 reads only `task2_realtime_prefix5/` files; Task 1 uses the production 34 columns (including the disclosed Task 2
columns). Train + validation labels only; test features only for the test-effect check. No decoded sizes. No upload.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-18 | Protocol frozen and committed | before any code change or run |
| 2026-10-18 | Runner committed (`cf166c8`); smoke check (fold 0 of 2151) | the rebuild with no layer dropped equals `models.task1_cross_task` on 66 of 66 flows; drops change 0-2 predictions |
| 2026-10-18 | All arms on cv_seeds 2151-2155 (`--all`) | 50 runs `…_112_<arm>_s<seed>` |
| 2026-10-18 | `--analyse`, `--test-effect`; `runs.py verify` | `analysis.json`, `test_effect.json`; 791 of 791 runs verified |

No deviation from the frozen protocol.

### Commands

```bash
.venv/bin/python src/exp112_layer_audit.py --smoke
.venv/bin/python src/exp112_layer_audit.py --all
.venv/bin/python src/exp112_layer_audit.py --analyse
.venv/bin/python src/exp112_layer_audit.py --test-effect
```

## Results

Removal Δ = arm − production, macro F1 on the same folds, mean of cv_seeds 2151-2155
([`112_evidence/analysis.json`](112_evidence/analysis.json), [`test_effect.json`](112_evidence/test_effect.json)):

| Layer removed | Removal Δ | Seeds with Δ < 0 | Seeds BETTER (removal) | Fixed / broken (5 seeds) | Test changes | Reading |
|---|---:|---:|---:|---|---:|---|
| 014 facebook/instagram specialist (Task 2) | **−0.0205** | 5 | 0 | 0 / 108 | 0 | earns its place |
| 087 instagram rule | **−0.0101** | 5 | 0 | 19 / 64 | 0 | earns its place |
| 036 exact-opening rule | **−0.0091** | 5 | 0 | 1 / 202 | 1 | earns its place |
| 100 cross-task rescue | **−0.0083** | 5 | 0 | 3 / 50 | 1 | earns its place |
| 065 rest-of-flow expert | **−0.0077** | 5 | 0 | 137 / 266 | 2 | earns its place |
| 028 opening expert | −0.0022 | 4 | 0 | 285 / 298 | 3 | earns its place (narrowly) |
| 084 pair verifiers | −0.0013 | 4 | 0 (WORSE on 4) | 36 / 96 | 0 | earns its place |
| **034 Meta gate** | **+0.0046** | **0** | 2 | **37 / 1** | **0** | inconclusive by the frozen rule |

**The 034 Meta gate, in detail:** removal Δ +0.0029 / +0.0043 / +0.0042 / +0.0033 / +0.0084; wins / losses 6/0, 9/0, 10/0
(BETTER), 7/1, 14/1 (BETTER): 46 wins and 2 losses over 250 folds, 204 ties. Per seed, too few folds change to reach rule v2's 10
non-tied folds. Facebook +0.024, google +0.002, youtube +0.002. Main moves: false facebook calls removed (google 12, x 9,
instagram 6 flows back to their own or another app), facebook flows gained from mozilla, google and x (10), youtube flows freed from
google (10).

## Verdict

**Production stands; 113 is not run.**

1. **Seven of eight layers earn their place** on fresh seeds: removing any of them lowers macro F1 (the 014 specialist, 087, 036,
   100 and 065 on all five seeds).
2. **The 034 Meta gate has become redundant.** Adopted on 2026-10-01 as a deliberate exception (it moved flows into Meta), it now
   sits under layers that do its job better (087 rule, 084 verifiers, 100 rescue). Removing it helps on every seed (46 wins, 2
   losses) but changes so few folds that rule v2 rates only 2 of 5 seeds BETTER. This is the path dependence Sid suspected: an
   early layer that later layers made obsolete.
3. **It cannot move the score:** without the gate, the Task 1 test file is identical to production 100 (0 changes). So by the
   pre-registered rule 113 is not triggered, and even a simplified model would not change the leaderboard. The finding goes to
   the technical report (a simpler equivalent model) and to any post-deadline clean-up.
