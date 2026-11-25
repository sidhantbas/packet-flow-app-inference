---
title: "108: Does an exact-opening lookup improve our Task 2 production model?"
created: 2026-10-13
creator: sidhantbas
description: "Frozen test of the last leader technique not yet tried on our own production: LLM_ops's exact first-5 lookup, ported to Task 2 as 036's scoped exact-opening override (and an unscoped variant) on top of models.task2_model. Never-used seeds 2131-2135."
source:
  - 103_lookup_ensemble_reproduction.md
  - 036_twin_aware.md
  - 035_h1_checks.md
  - ../docs/reports/leaders-vs-ours-dedup.md
experiment:
  id: '108'
  tasks: [task2]
  lever: hierarchy
  status: rejected
  verdict: 'No gain: our Task 2 production already predicts the label of every single-label exact opening it meets; the override changes 6 of 1650 held-out predictions (all mozilla -> google, all right), mean +0.0003, INCONCLUSIVE on 5 of 5 seeds; 0 test changes'
---

# 108: Exact-opening lookup on top of Task 2 production

**Status: done 2026-10-13. Protocol frozen (`bc20954`) before any code or run.**
**Verdict: no gain (production already does the lookup); not adopted.** Results are below the protocol. Sid, 2026-10-13: the leaders "may not disclose what exactly
happened, so we need to find out what it could be and then ... reproduce some experiments which have good chances to close up
the gaps."

## Question and evidence

- **Why now:** the deduplication of the leaders' techniques against ours ([report](../docs/reports/leaders-vs-ours-dedup.md))
  found one technique tested only on a leader's base, never on our production: LLM_ops's exact first-5 lookup. In 103 it added
  **+0.057 on Task 2** over their base (and −0.005 on Task 1). On Task 1 our production already has it (036 scoped override,
  inside 089). On Task 2 it was never tried.
- **What argues against it:** our Task 2 trees already memorise exact openings (016: bigger leaves hurt), and the unscoped rule
  hurt Task 1 (035: −0.0345). 256 of the 330 labelled flows share their exact 12-column opening with another flow.
- **Gap it could address:** Task 2 is 1.5 points behind the leader (about 2 flows of 81).

## Frozen design (Task 2)

Key = the 12 Task 2 production columns (`cv.no_timing_features`), exact equality, no rounding. The table holds the training-fold
openings that carry a **single** label L.

| Arm | Labels |
|---|---|
| P | Production `models.task2_model` (014) |
| H | P; where the flow's opening is in the table with label L, and neither L nor P's call is facebook/instagram, predict L (036's rule) |
| HA | P; where the flow's opening is in the table with label L, predict L (unscoped, closest to the leader's lookup) |

- Nothing is tuned; no thresholds.
- **Folds:** repeated stratified 5 × 10 at cv_seeds **2131-2135** (0 runs in `results/`); model seed = fold index.
- **Smoke check:** on one fold, H and HA predictions equal P's wherever the opening is not in the table.
- **Reported:** paired Δ vs P per seed (rule v2), flows fixed / broken, per-class Δ.
- **Test-set effect (no labels):** each arm fitted on train + validation; Task 2 test predictions changed against our
  submitted Task 2 file (`submissions/production-100-cross-task/`).

## Decision rule

An arm counts only if it is rule v2 BETTER than P on **all five** seeds; if both pass, H is preferred (the smaller change). A
pass makes a production candidate (user decision) and an upload candidate only under the upload rule (at least 3 changed test
predictions). Otherwise not adopted.

## Boundaries

Task 2 reads only `task2_realtime_prefix5/` files (condition 2). Train + validation labels only; test features only for the
test-effect check. Task 1 is not touched. No upload.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-13 | Protocol frozen and committed | before any code or run |
| 2026-10-13 20:00 | Runner committed (`557537e`); smoke check | on fold 0, both arms equal P wherever the opening is unseen; 32 of 66 held-out openings are known with one label, 0 predictions change |
| 20:00-20:01 | P, H, HA on cv_seeds 2131-2135 (`--all`) | 15 runs `…_108_<arm>_s<seed>` (the `dirty-tree` warning lists only this batch's own run folders) |
| after the runs | `--analyse`, `--test-effect` | `experiments/108_evidence/analysis.json`, `test_effect.json` |

No deviation from the frozen protocol.

### Commands

```bash
.venv/bin/python src/exp108_task2_exact_opening_override.py --smoke
.venv/bin/python src/exp108_task2_exact_opening_override.py --all
.venv/bin/python src/exp108_task2_exact_opening_override.py --analyse
.venv/bin/python src/exp108_task2_exact_opening_override.py --test-effect
```

## Results

| Seed | 2131 | 2132 | 2133 | 2134 | 2135 | Mean |
|---|---:|---:|---:|---:|---:|---:|
| Δ macro F1, H − P | +0.0004 | 0.0000 | 0.0000 | +0.0005 | +0.0005 | **+0.0003** |
| Wins / losses / ties | 2 / 0 / 48 | 0 / 0 / 50 | 0 / 0 / 50 | 2 / 0 / 48 | 2 / 0 / 48 | |
| Verdict | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE | |

HA (unscoped) is identical to H on every fold: no single-label opening ever pointed into or out of facebook/instagram where
production disagreed. Over the five seeds the override changed **6 of 1650** held-out predictions, all mozilla → google, all
right (6 fixed, 0 broken). **Test-set effect:** 0 Task 2 predictions change in either arm.

## Verdict

**No gain, not adopted: our Task 2 production already does the lookup.** Its trees memorise exact openings (016), so wherever an
opening was seen with one label (about half the held-out flows), production already predicts that label; it disagreed only
6 times in 1650 held-out predictions. The +0.057 the lookup gave LLM_ops's base in 103 measures what their base lacked (probably
because their kNN and LightGBM members smooth over exact openings; not measured), not something ours lacks. With 102-108, every technique the leaders describe is tested or excluded. Status: rejected.
