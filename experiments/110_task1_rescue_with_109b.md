---
title: "110: Does 109 B's sharper facebook/instagram specialist improve Task 1's cross-task Meta rescue?"
created: 2026-10-17
creator: sidhantbas
description: "Frozen test of replacing the inner Task 2 model of Task 1's cross-task Meta rescue (100) with 109 B (facebook/instagram specialist with columns chosen per fold, incl. decoded opening sizes), with 100's trigger and a widened trigger, on never-used seeds 2141-2145."
source:
  - 100_cross_task_meta_rescue.md
  - 109_task2_first_packet_specialist.md
  - 090_stamp_catalogue.md
  - ../notebooks/code-walkthrough/06-leaderboard-comparison.ipynb
experiment:
  id: '110'
  tasks: [task1]
  lever: hierarchy
  status: rejected
  verdict: '109 B does not transfer to Task 1: C (100 trigger) −0.0059, facebook −0.033 (28 broken, 2 fixed); D (Meta trigger) +0.0004, 15 fixed, 33 broken (26 google flows pulled into facebook); no seed BETTER; 0 test changes'
---

# 110: 109 B inside Task 1's cross-task Meta rescue

**Status: done 2026-10-18. Protocol frozen (`faef096`) before any code or run.**
**Verdict: rejected. The sharper specialist does not help Task 1's rescue: C loses facebook flows, D trades them for false
facebook calls; no seed is BETTER and no test prediction changes.** Results are below the protocol.
Do not edit the frozen sections after execution starts. Sid, 2026-10-17: "go ahead and run 110", after the gap analysis showed
Task 1's expensive facebook/instagram errors hold about 4 of the 6.9 points to the leader (notebook 6).

## Question and evidence

- **Gap:** the leader's Task 1 errors cost 0.45 points each, ours 1.02 (16 October leaderboard; notebook 6). An error involving
  facebook costs 1.3-2.4 points, one among google/x/youtube/mozilla 0.36-0.75.
- **Production Task 1 (100 FB):** the 089 bundle plus an inner copy of the Task 2 model (014) on the 12 opening columns; a flow the
  inner model calls **instagram** while the bundle calls it non-Meta becomes **facebook** (100: such flows were facebook 137 of
  138 times; labelling them instagram did not help, arm IG).
- **109 B:** a Task 2 facebook/instagram specialist with columns chosen by nested forward selection (mostly the decoded first-packet
  size `s_up_max`) was +0.0197 on Task 2 on all five never-used seeds (BETTER on 3 of 5), facebook and instagram F1 about +0.06
  each.
- **Question:** if the inner model's facebook/instagram calls get sharper, does the rescue fix more Task 1 Meta flows?
- **Why a widened trigger:** a sharper inner model may call some of the rescued facebook flows *facebook* rather than
  *instagram*; 100's trigger (instagram only) would then miss them.

## Frozen design (Task 1)

Inputs: the 34 production Task 1 columns (`cv.task1_with_prefix_features`), as production. The inner model sees only the 12 `p5_`
opening columns without timing (renamed to Task 2 names, as 100), plus columns derived from them inside the model: the 10
engineered columns and 8 decoded sizes of 109 (the decoded sizes are computed from `p5_transport`, packet counts, mean and std
sizes; no other input).

| Arm | Inner Task 2 model | Rescue trigger (bundle calls neither facebook nor instagram) |
|---|---|---|
| P | `models.task2_model` (014) | inner calls instagram → facebook (production 100 FB) |
| C | 109 B (`SelectSpecialist`, same settings as 109) | inner calls instagram → facebook (100's trigger unchanged) |
| D | 109 B | inner calls facebook **or** instagram → facebook |

- The 089 bundle is unchanged in every arm, so flows the bundle calls facebook or instagram are never touched.
- Nothing is tuned.
- **Folds:** repeated stratified 5 × 10 on cv_seeds **2141-2145** (0 runs in `results/`); model seed = fold index.
- **Smoke check (one fold):** P equals `models.task1_cross_task` exactly; C and D agree with P wherever the bundle calls facebook
  or instagram; the decoded sizes from the `p5_` columns equal 109's decoded sizes from the Task 2 file for the same flows.
- **Reported:** paired Δ vs P per seed (rule v2), per-class Δ, flows fixed / broken, rescue cases per arm; test-set effect: each
  arm fitted on train + validation, Task 1 test predictions changed against every earlier uploaded file kept in `submissions/`
  (no test labels exist or are read).

## Decision rule

An arm counts only if it is rule v2 BETTER than P on **all five** seeds; if both pass, C is preferred (the smaller change). A pass
is evidence only. Production use additionally needs (1) the user's decision, (2) a decision by Sid and Charles that the decoded
sizes are acceptable under challenge condition 3 (see 109), and (3) disclosure in the technical report (Task 1 already contains a
model trained on Task 2 files, disclosed for 022 and 100). An upload also needs the upload rule: rule v2 on never-used seeds and at
least 3 test predictions different from every earlier upload. Otherwise not adopted.

## Boundaries

- Task 1 may read Task 2 files (condition 2 restricts only Task 2); here the inner model uses only the `p5_` columns already in
  production Task 1's input. Task 2 is not touched.
- Train + validation labels only; test features only for the test-effect check. No upload.
- Condition 3: the same open question as 109 (`s_up_max` may depend on the server name's length); no name, address or content is
  decoded.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-17 | Protocol frozen and committed | before any code change or run |
| 2026-10-17 22:45 | Runner committed (`5f50854`); smoke check | decoded sizes from `p5_` columns equal 109's from the Task 2 file; on one fold of 2141, C and D equal P wherever the bundle calls Meta, 0 of 66 predictions changed |
| 22:48-23:08 | P, C, D on cv_seeds 2141-2145 (`--all`) | 15 runs `…_110_<arm>_s<seed>`; inner selections in `110_evidence/selected_columns.jsonl` (500 fits, C and D identical) |
| 2026-10-18 | `--analyse`, `--test-effect`; `runs.py verify` | `analysis.json`, `test_effect.json`; 726 of 726 runs verified |

No deviation from the frozen protocol.

### Commands

```bash
.venv/bin/python src/exp110_task1_rescue_with_109b.py --smoke
.venv/bin/python src/exp110_task1_rescue_with_109b.py --all
.venv/bin/python src/exp110_task1_rescue_with_109b.py --analyse
.venv/bin/python src/exp110_task1_rescue_with_109b.py --test-effect
```

## Results

Task 1 macro F1 vs P on the same folds (from each run's `comparison.json`; [`110_evidence/analysis.json`](110_evidence/analysis.json)):

| Seed | C vs P (W / L / T) | Verdict | D vs P (W / L / T) | Verdict |
|---|---|---|---|---|
| 2141 | −0.0086 (0 / 7 / 43) | INCONCLUSIVE | −0.0008 (3 / 7 / 40) | WORSE |
| 2142 | −0.0104 (1 / 5 / 44) | INCONCLUSIVE | −0.0010 (1 / 6 / 43) | INCONCLUSIVE |
| 2143 | −0.0006 (1 / 2 / 47) | INCONCLUSIVE | −0.0026 (1 / 7 / 42) | INCONCLUSIVE |
| 2144 | −0.0035 (0 / 4 / 46) | INCONCLUSIVE | +0.0041 (5 / 6 / 39) | INCONCLUSIVE |
| 2145 | −0.0064 (0 / 6 / 44) | INCONCLUSIVE | +0.0021 (5 / 6 / 39) | INCONCLUSIVE |
| **Mean** | **−0.0059** | 0 of 5 BETTER | **+0.0004** | 0 of 5 BETTER |

- **Per class (mean):** C facebook **−0.033**, google −0.002; D facebook +0.003, google −0.002; others about 0.
- **Changed held-out predictions (5 seeds × 330 flows):** C 32 (2 fixed, **28 broken**): facebook flows P had rescued go back
  to google (23). D 52 (15 fixed, **33 broken**): it rescues facebook flows from x, google, mozilla and youtube (15), but pulls
  26 google, 5 x and 2 mozilla flows into facebook.
- **Inner selection (500 fits, C and D identical):** `s_up_max` 270, `e_cv_size_up` 118, `s_up_min` 84, `burst_count` 54,
  `s_syn_size` 52.
- **Test-set effect** ([`110_evidence/test_effect.json`](110_evidence/test_effect.json)): fitted on train + validation, C and D
  change **0** Task 1 test predictions against production 100 (and so 0 against at least one earlier upload).

## Verdict

**Rejected.** 109 B's sharper facebook/instagram decisions do not transfer to Task 1's rescue. The reason is visible in the
changes:

1. **Production's rescue works *because of* 014's confusion.** 014 calls many true facebook openings "instagram", and 100's rule
   turns exactly those into facebook. 109 B now calls them "facebook", so 100's trigger (C) stops firing and 23 rescued facebook
   flows fall back to google.
2. **Widening the trigger (D) restores those rescues but adds false ones.** 109 B's "facebook" calls on openings include many
   google flows (the 1365-byte first packet is shared by 30 google flows, 109's table), so 26 google flows become facebook. Net
   effect zero.
3. **No test prediction changes**, so even a pass could not have been uploaded.

What it means for the gap: Task 1's expensive Meta errors are not reachable by sharpening the opening-based rescue. 109 B stays a
Task 2-only candidate (waiting on the condition 3 decision). Production unchanged: Task 1 = 100 FB, Task 2 = 014.
