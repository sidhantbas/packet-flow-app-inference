---
title: "109: Does the decoded first-packet size improve Task 2's facebook/instagram specialist?"
created: 2026-10-15
creator: sidhantbas
description: "Frozen test of giving Task 2's facebook/instagram specialist (014) the client's decoded first-packet size (s_up_max, 090), either added to its 12 columns or through nested forward selection, judged on the full 6-app Task 2 pipeline on never-used seeds 2136-2140."
source:
  - 090_stamp_catalogue.md
  - 014_fb_ig_specialist.md
  - 012_class_weights.md
  - ../notebooks/code-walkthrough/05-facebook-instagram.ipynb
experiment:
  id: '109'
  tasks: [task2]
  lever: features
  status: inconclusive
  verdict: 'B (nested selection, mostly s_up_max) +0.0197 mean, Δ > 0 on 5 of 5 seeds but BETTER on 3 of 5 (2136, 2139 near-miss at 68%); facebook +0.060, instagram +0.058; A (add s_up_max) +0.0018, too few changes; frozen rule (5 of 5) not met; 1 test change (B); not adopted'
---

# 109: The decoded first-packet size in Task 2's facebook/instagram specialist

**Status: done 2026-10-15. Protocol frozen (`631e6b4`) before any code or run.**
**Verdict: B is positive on all five seeds (mean +0.0197) but BETTER on only 3 of 5, so the frozen rule is not met; A changes
almost nothing. Not adopted.** Results are below the protocol.
Do not edit the frozen sections after execution starts. Sid, 2026-10-15: "okay run the decoded first packet size", after the
facebook/instagram deep dive in notebook 5.

## Question and evidence

Facebook vs instagram is Task 2's most costly confusion: if it were fixed perfectly, Task 2 cross-validation macro F1 would rise
from 0.754 to 0.865 (+5.5 points), against +2.1 points for google vs youtube. Only the specialist (014) decides between the two
apps. In notebook 5 (cv_seed 2026, the 30 Meta flows only, facebook vs instagram):

| Specialist model (two-app score) | Two-app macro F1 | AUC |
|---|---|---|
| Current specialist: unweighted SoftVote, 12 columns (part 7) | 0.636 | 0.607 |
| Nested forward selection from 30 candidates incl. 8 decoded sizes (part 6, balanced SoftVote) | 0.685 | 0.646 |
| The same without the decoded sizes | 0.617 | 0.591 |

The gain comes from `s_up_max`, the largest upstream packet of the opening (the client's first message), decoded exactly from
`packet_count_up`, `mean_pkt_size_up` and `std_pkt_size_up` (090): 1367 B in 16 of 19 instagram and 3 of 11 facebook flows,
1365 B in 4 facebook, 1 instagram and 30 google flows. Earlier, the decoded sizes added to the whole model tied (090: AUC +0.016;
093 H1: TIE), so the open question is whether they help **where only facebook and instagram are decided**.

**Post hoc:** both arms were designed after notebook 5 looked at these 330 flows on cv_seed 2026. That is why only never-used
seeds count.

## Frozen design (Task 2)

Base for every arm: production `models.task2_model` (014). Its 6-app balanced SoftVote on the 12 production columns
(`cv.no_timing_features`) is unchanged; only the specialist that re-decides flows called facebook or instagram differs.

| Arm | Specialist (trained on the facebook + instagram training rows only, unweighted SoftVote as in 014) |
|---|---|
| P | Production: the 12 production columns |
| A | **Add**: the 12 production columns + `s_up_max` (13 columns); `models.PairSpecialist(base_cols=12 columns, spec_all_cols=True)` |
| B | **Select**: columns chosen inside each training fold by nested forward selection (as notebook 5 part 6) from 30 candidates |

- `s_up_max` and the other decoded sizes: `src/exp090_stamp_catalogue.stamps` on each raw Task 2 row; undecodable = −1.
- B's 30 candidates: the 12 production columns; 10 engineered columns (notebook 5 part 5: total bytes and packets, downstream
  byte and packet share, mean size down − up, bytes and packets per burst, size std ÷ mean up and down, opening bytes per
  packet); 8 decoded sizes (`syn_size`, `hello_size`, `synack_size`, `reply_size`, `up_min`, `up_max`, `down_min`, `down_max`).
- B's selection (inside the specialist's `fit`, on its facebook + instagram rows only): start empty; add the column that most
  raises the inner AUC (repeated stratified 3-fold × 2, `random_state` = model seed, balanced random forest with 100 trees);
  stop when the gain is below 0.005 or at 5 columns; if nothing is chosen, use the single best column by single-column AUC.
- Nothing else is tuned.
- **Folds:** repeated stratified 5 × 10 on cv_seeds **2136-2140** (0 runs in `results/`); model seed = fold index.
- **Smoke check (one fold):** P equals `models.task2_model` exactly; A and B agree with P on every flow P's base calls neither
  facebook nor instagram.
- **Reported:** paired Δ vs P per seed (rule v2), per-class Δ, flows fixed / broken, B's chosen columns per fold; test-set
  effect: each arm fitted on train + validation, Task 2 test predictions changed against the submitted Task 2 file
  (`submissions/production-100-cross-task/`); no test labels exist or are read.

## Decision rule

An arm counts only if it is rule v2 BETTER than P on **all five** seeds; if both pass, A is preferred (the smaller change). A
pass is evidence only. Production use additionally needs (1) the user's decision, (2) a decision by Sid and Charles that
`s_up_max` is acceptable under challenge condition 3 (below), and (3) disclosure in the technical report. An upload also needs
the upload rule: rule v2 on never-used seeds and at least 3 test predictions different from every earlier upload. Otherwise not
adopted.

## Boundaries

- Task 2 reads only `task2_realtime_prefix5/` files (condition 2); the decoded sizes come from Task 2 columns only.
- Train + validation labels only; test features only for the test-effect check. No upload.
- **Condition 3 (open question):** `s_up_max` is the size of the client's first message. For TCP that is the TLS ClientHello,
  whose length depends partly on the server name; the 2-byte QUIC difference may have the same cause (not verified). No name,
  address or content is decoded and no size is mapped to a domain; the size is used only as a number. Whether that is
  acceptable is not decided by this experiment.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-15 | Protocol frozen and committed | before any code change or run |
| 2026-10-15 22:37 | Runner committed (`e7bba61`); smoke check | on one fold of seed 2136, A and B equal P on every flow P's base calls neither facebook nor instagram; 6 base Meta calls, 1 prediction changed by each |
| 22:38-22:47 | P, A, B on cv_seeds 2136-2140 (`--all`) | 15 runs `…_109_<arm>_s<seed>`; B's chosen columns logged to `experiments/109_evidence/selected_columns.jsonl` (250 fits) |
| after the runs | `--analyse`, `--test-effect`; `runs.py verify` | `analysis.json`, `test_effect.json`; 711 of 711 runs verified |

No deviation from the frozen protocol.

### Commands

```bash
.venv/bin/python src/exp109_task2_first_packet_specialist.py --smoke
.venv/bin/python src/exp109_task2_first_packet_specialist.py --all
.venv/bin/python src/exp109_task2_first_packet_specialist.py --analyse
.venv/bin/python src/exp109_task2_first_packet_specialist.py --test-effect
```

## Results

Task 2 macro F1 (mean of 50 folds) per seed, and the paired comparison with P on the same folds (from each run's
`comparison.json`; evidence in [`109_evidence/analysis.json`](109_evidence/analysis.json)):

| Seed | P | A | A vs P | B | B vs P |
|---|---|---|---|---|---|
| 2136 | 0.7669 | 0.7673 | +0.0004 (1 W / 0 L / 49 T), INCONCLUSIVE | 0.7872 | **+0.0203** (15 / 7 / 28), NEAR-MISS |
| 2137 | 0.7609 | 0.7635 | +0.0026 (2 / 0 / 48), INCONCLUSIVE | 0.7771 | **+0.0162** (15 / 5 / 30), **BETTER** |
| 2138 | 0.7599 | 0.7626 | +0.0027 (3 / 0 / 47), INCONCLUSIVE | 0.7840 | **+0.0241** (20 / 4 / 26), **BETTER** |
| 2139 | 0.7609 | 0.7609 | 0.0000 (0 / 0 / 50), INCONCLUSIVE | 0.7691 | **+0.0082** (13 / 6 / 31), NEAR-MISS |
| 2140 | 0.7599 | 0.7630 | +0.0031 (3 / 0 / 47), INCONCLUSIVE | 0.7895 | **+0.0295** (17 / 6 / 27), **BETTER** |
| **Mean** | | | **+0.0018** | | **+0.0197** |

- **Per class (mean over seeds):** B facebook **+0.060**, instagram **+0.058**, other apps 0 (the base model is unchanged).
  A facebook +0.003, instagram +0.007.
- **Held-out predictions changed (5 seeds × 330 flows):** A 11 (10 fixed, 0 broken, all instagram flows that P called
  facebook). B 156 (101 fixed, 14 broken; the rest wrong before and after). B's main moves: instagram flows from facebook to
  instagram (62), facebook flows from instagram to facebook (39); youtube flows that P had called instagram now called facebook
  (22, still wrong); google flows from facebook to instagram (16, still wrong).
- **B's chosen columns (250 fits):** `s_up_max` in 142, `e_cv_size_up` 58, `s_up_min` 35, `s_syn_size` 31, `burst_count` 24;
  1 column in 140 fits, 2 in 76, 3 in 30, 4 in 4.
- **Test-set effect** ([`109_evidence/test_effect.json`](109_evidence/test_effect.json)), each arm fitted on train +
  validation, against the submitted Task 2 file: P 0 changes, A 0, **B 1** (`flow_001187` instagram → facebook). Fitted on all
  330 flows, B's specialist chose a single column, `s_up_min` (the smallest upstream packet of the opening), not `s_up_max`.

## Verdict

**Not adopted under the frozen rule.** B, the specialist that picks its columns inside each training fold, is the clearest Task 2
facebook/instagram gain the project has measured: Δ > 0 on all five never-used seeds, mean +0.0197 (about +1.0 Task 2 point in
CV), facebook and instagram F1 both about +0.06, and no change to the other apps. It is rule v2 BETTER on 3 of 5 seeds; on 2136
and 2139 it wins 68% of the non-tied folds (15 of 22, 13 of 19) against the 70% needed. The protocol required all five, so it
fails. A, adding `s_up_max` to the 12 columns, barely moves the specialist (11 changed predictions in 1,650): trees given 13
columns hardly use the one new column, which matches 090 and 093, where the decoded sizes added to full models tied.

What it means:

1. **Choosing few columns matters as much as the column.** The decoded sizes help only when the specialist is restricted to 1 or
   2 columns (notebook 5 part 6 showed the same on cv_seed 2026).
2. **It would not change the test file enough to upload:** 1 changed Task 2 prediction, against the upload rule's 3.
3. **Adopting it anyway would be a deliberate exception** (as 028, 034 and 100 were), needing the user's decision **and** a
   decision by Sid and Charles that the decoded sizes are acceptable under condition 3, with disclosure in the report. The final
   fitted model uses `s_up_min`. That carries the same caveat: when the opening has a single upstream packet, the smallest
   upstream packet *is* the first packet (1365 or 1367 B), and the fold-level selections lean on `s_up_max`.

Production unchanged: Task 1 = 100 FB, Task 2 = 014.
