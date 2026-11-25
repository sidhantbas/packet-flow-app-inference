---
title: "111: Does a jointly fitted stacker beat the hand-coded cross-task rescue in Task 1?"
created: 2026-10-18
creator: sidhantbas
description: "Frozen test of replacing Task 1's hand-coded cross-task Meta rescue (100) by a logistic-regression stacker learned inside each training fold from out-of-fold base-model outputs (014 opening model, optionally 109 B, and the 089 bundle's label), on never-used seeds 2146-2150."
source:
  - 100_cross_task_meta_rescue.md
  - 110_task1_rescue_with_109b.md
  - 109_task2_first_packet_specialist.md
  - 019_stacking.md
experiment:
  id: '111'
  tasks: [task1]
  lever: hierarchy
  status: rejected
  verdict: 'Learned stacker loses to the hand rule: S14 −0.0129, S −0.0131, behind on 5 of 5 seeds (WORSE on 2); facebook −0.068; it almost never fires (4 fixed, 60 broken: production''s rescues lost); 109 B adds nothing (S ≈ S14); test: undoes production''s one rescue'
---

# 111: A jointly fitted stacker instead of the hand-coded rescue

**Status: done 2026-10-18. Protocol frozen (`05b4e57`) before any code or run.**
**Verdict: rejected. The learned stacker almost never fires, so it loses the facebook flows the hand rule rescues; worse on all five
seeds.** Results are below the protocol.
Do not edit the frozen sections after execution starts. Sid, 2026-10-18: "fit the stacker jointly and run it as 111".

## Question and evidence

- **100's rescue is a hand-fitted meta-rule** on two base outputs: inner opening model 014 says instagram and the 089 bundle says
  non-Meta → facebook. It was calibrated once on 014's error structure.
- **110 showed the entanglement:** swapping the inner model for the sharper 109 B without refitting the rule broke it (C −0.0059:
  109 B stops calling facebook openings "instagram"); widening the trigger traded rescues for false facebook calls (D +0.0004).
- **The principled remedy** is to *learn* the meta-rule jointly, inside each training fold, from out-of-fold base outputs, so the
  rule always matches whichever base models it sits on.
- **Risk known in advance:** learned combiners were unstable when fitted on few Meta cases (019: facebook −0.17 to −0.24). The
  design below limits that variance: the stacker learns "is this flow facebook?" from all training flows (about 9 facebook
  flows per training fold), with few inputs and a regularised linear model, and it can only act where 100's rule acts.

## Frozen design (Task 1)

Inputs: the 34 production Task 1 columns (`cv.task1_with_prefix_features`). Base models as in production: the 089 bundle
(`models.task1_bundle`) on all 34 columns; the inner opening model on the 12 `p5_` columns renamed to Task 2 names (014:
`models.task2_model`; 109 B: `exp109.SelectSpecialist` on 109's 30 candidates built from those columns, as in 110).

**Stacker, fitted inside each training fold:**

1. Inner stratified 4-fold on the training fold (`random_state` = model seed): base models fitted on 3/4, predicting the left-out
   1/4, give out-of-fold stacker inputs for every training flow.
2. Stacker inputs per flow:
   - `p_meta`: the 014 base SoftVote's P(facebook) + P(instagram) on the opening;
   - `p_fb_014`: 014's facebook/instagram specialist P(facebook) (unweighted SoftVote on the 12 opening columns);
   - `p_fb_109b` (arm S only): 109 B's specialist P(facebook) on its selected columns;
   - the bundle's label, one-hot over the 6 apps.
3. Target: the flow is facebook (all training flows).
4. Model: standardised inputs, L2 logistic regression (C = 1.0, unweighted, `max_iter` 1000).
5. Base models are then refitted on the whole training fold. On held-out flows: **flows the bundle calls facebook or instagram
   keep the bundle's label** (as in 100). Every other flow becomes facebook if the stacker's P(facebook) > 0.5, otherwise it
   keeps the bundle's label. If a training fold's out-of-fold rows hold no facebook flow, the stacker never fires.

| Arm | Inner models feeding the stacker |
|---|---|
| P | Production `models.task1_cross_task` (100 FB: the hand-coded rule) |
| S14 | 014 only (`p_meta`, `p_fb_014`, bundle one-hot): the learned version of 100's rule, **no decoded sizes** |
| S | 014 and 109 B (adds `p_fb_109b`): uses the decoded first-packet size |

- Nothing is tuned; the 0.5 cut-off and C = 1.0 are fixed here.
- **Folds:** repeated stratified 5 × 10 on cv_seeds **2146-2150** (0 runs in `results/`); model seed = fold index.
- **Smoke check (one fold):** P equals `models.task1_cross_task`; S14 and S keep the bundle's label wherever it calls Meta; the
  out-of-fold stacker inputs cover every training flow; the stacker coefficients and the number of rescues are printed.
- **Reported:** paired Δ vs P per seed (rule v2), per-class Δ, flows fixed / broken; test-set effect: each arm fitted on train +
  validation, Task 1 test predictions changed against every earlier uploaded file in `submissions/` (no test labels exist or are
  read).

## Decision rule

An arm counts only if it is rule v2 BETTER than P on **all five** seeds. If both pass, **S14 is preferred**: it uses no decoded
sizes, so it raises no condition 3 question. A pass is evidence only; production use needs the user's decision (and, for S, the
condition 3 decision by Sid and Charles), with disclosure in the report. An upload also needs the upload rule (rule v2 on
never-used seeds and at least 3 test predictions different from every earlier upload). Otherwise not adopted.

## Boundaries

- Task 1 may read Task 2 files (condition 2 restricts only Task 2); the inner models use only the `p5_` columns already in
  production Task 1's input. Task 2 is not touched.
- Train + validation labels only, and inside each outer training fold only; test features only for the test-effect check. No
  upload.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-18 | Protocol frozen and committed | before any code change or run |
| 2026-10-18 | Runner committed (`b156a00`); smoke check (fold 0 of 2146) | out-of-fold inputs for 264 of 264 training flows (9 facebook); bundle labels kept on Meta calls; **0 rescues** in both arms vs 3 by the hand rule (warned before the run; the frozen cut-off was kept) |
| 2026-10-17 23:22 – 2026-10-18 00:28 | P, S14, S on cv_seeds 2146-2150 (`--all`) | 15 runs `…_111_<arm>_s<seed>` |
| 2026-10-18 | `--analyse`, `--test-effect`; `runs.py verify` | `analysis.json`, `test_effect.json`; 741 of 741 runs verified |

No deviation from the frozen protocol.

### Commands

```bash
.venv/bin/python src/exp111_task1_learned_rescue_stacker.py --smoke
.venv/bin/python src/exp111_task1_learned_rescue_stacker.py --all
.venv/bin/python src/exp111_task1_learned_rescue_stacker.py --analyse
.venv/bin/python src/exp111_task1_learned_rescue_stacker.py --test-effect
```

## Results

Task 1 macro F1 vs P on the same folds ([`111_evidence/analysis.json`](111_evidence/analysis.json)):

| Seed | S14 vs P (W / L / T) | Verdict | S vs P (W / L / T) | Verdict |
|---|---|---|---|---|
| 2146 | −0.0152 (4 / 12 / 34) | WORSE | −0.0156 (4 / 13 / 33) | WORSE |
| 2147 | −0.0144 (1 / 11 / 38) | WORSE | −0.0144 (1 / 11 / 38) | WORSE |
| 2148 | −0.0140 (6 / 10 / 34) | INCONCLUSIVE | −0.0140 (6 / 10 / 34) | INCONCLUSIVE |
| 2149 | −0.0107 (4 / 7 / 39) | INCONCLUSIVE | −0.0114 (4 / 8 / 38) | INCONCLUSIVE |
| 2150 | −0.0100 (6 / 8 / 36) | INCONCLUSIVE | −0.0100 (6 / 8 / 36) | INCONCLUSIVE |
| **Mean** | **−0.0129** | 0 of 5 BETTER | **−0.0131** | 0 of 5 BETTER |

- **Per class (mean):** S14 facebook **−0.068**, google −0.005, mozilla −0.003; S the same within 0.001.
- **Changed held-out predictions (5 seeds × 330 flows):** S14 102 (4 fixed, **60 broken**), S 104 (4 fixed, 62 broken). Almost
  every change is a production rescue undone: facebook flows that P had turned into facebook fall back to google (59); true
  instagram flows that P had wrongly called facebook go to google or mozilla (28, wrong either way).
- **Stacker fitted on all 330 flows** ([`111_evidence/test_effect.json`](111_evidence/test_effect.json)): the largest weights
  are on the bundle's own label (`b_facebook` +1.22, `b_instagram` +1.01); `p_meta` −0.13, `p_fb_014` −0.36, `p_fb_109b` +0.12.
- **Test-set effect:** both arms change 1 Task 1 test prediction against production 100 (`flow_000223` facebook → youtube),
  undoing production's single test rescue; that equals an earlier upload (0 changes against upload 7).

## Verdict

**Rejected.** Learning the rescue rule jointly does not beat the hand-coded rule; it is worse on all five seeds. Why:

1. **The stacker learns the easy pattern, not the rescue.** Trained on all training flows, "is this flow facebook?" is answered
   mostly by the bundle's own label (facebook flows the bundle already calls facebook). Among flows the bundle calls non-Meta,
   facebook is rare (a few per fold), so P(facebook) almost never passes 0.5 and the stacker stays silent.
2. **The hand rule encodes a pattern too rare to learn** from about 9 facebook flows per fold (2-3 rescue cases), but stable
   enough to measure across 50 folds (100: 137 of 138). Fitted by hand on the pooled cross-validation of 100, it captured that
   pattern; a per-fold learner cannot. This is the same variance limit as 019 (learned combiner, facebook −0.17 to −0.24).
3. **109 B adds nothing once the rule is learned** (S ≈ S14), so 110 and 111 together close the "Task 2 specialist into Task 1"
   direction.

Production unchanged: Task 1 = 100 FB, Task 2 = 014.
