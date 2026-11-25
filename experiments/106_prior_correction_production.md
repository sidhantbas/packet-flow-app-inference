---
title: "106: Does LLM_ops's prior correction (beta = 0.25) improve our Task 1 production model?"
created: 2026-10-13
creator: sidhantbas
description: "Frozen test of the one open lead from the leader reproductions: prior correction of the experts' averaged probabilities inside our Task 1 production (100) before the Meta gate decides, beta fixed at 0.25 as claimed. Never-used seeds 2121-2125."
source:
  - 103_lookup_ensemble_reproduction.md
  - 100_cross_task_meta_rescue.md
  - ../docs/reports/leaderboard-method-reproduction.md
experiment:
  id: '106'
  tasks: [task1]
  lever: decision
  status: rejected
  verdict: 'Not adopted: prior correction beta=0.25 inside production is BETTER on 1 of 5 never-used seeds (mean +0.0010); 1 test prediction would change'
---

# 106: Prior correction on top of Task 1 production

**Status: done 2026-10-13. Protocol frozen (`4057c43`) before any code or run.**
**Verdict: not adopted (mean +0.0010, BETTER on 1 of 5 seeds).** Results are below the protocol. Sid, 2026-10-13: after
deduplicating the leaders' techniques, "reproduce some experiments which have good chances to close up the gaps".

## Question and evidence

LLM_ops's note includes "mild prior correction (β=0.25) guards macro-F1 on rare classes". In 103 it improved their Task 1 ladder
on every seed (+0.006, 113 W / 58 L) and hurt Task 2. It is allowed in a submission and was never tested on our production.

## Frozen design (Task 1)

- **P:** production `models.task1_cross_task` (100).
- **B25:** production with one change: inside the Meta gate (089's `RestIGMetaGate`), the averaged probabilities of the three
  experts are prior-corrected before the gate decides, $p_c \propto p_c / \pi_c^{0.25}$, with $\pi$ the training class shares
  (`flowkit.postprocess.prior_correct`). The facebook/instagram choice, the 087 rule, the 084 verifiers, the scoped H1 override
  and the cross-task rescue are unchanged. β is the claimed 0.25; nothing is tuned.
- **Folds:** repeated stratified 5 × 10 at cv_seeds **2121-2125** (0 runs in `results/`); model seed = fold index.
- **Smoke check:** with β = 0 the modified model reproduces production's predictions exactly on one fold.
- **Test-set effect (no labels):** B25 fitted on train + validation; test predictions changed against our submitted Task 1.

## Decision rule

Rule v2 BETTER than P on all five seeds. On a pass: a production candidate (user decision), and an upload only under the upload
rule (at least 3 changed test predictions). Otherwise not adopted.

## Boundaries

Train + validation labels only; test features only for the test-effect check. Task 2 is not touched. No upload.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-13 | Protocol frozen and committed | before any code or run |
| 2026-10-13 19:15 | Runner committed (`92e178e`); smoke check | β = 0 reproduces production exactly on one fold; β = 0.25 changes 1 of 66 predictions there |
| 19:16-19:20 | P and B25 on cv_seeds 2121-2125 (`--all`) | 10 runs `…_106_<arm>_s<seed>` |
| after the runs | `--analyse`, `--test-effect` | `experiments/106_evidence/analysis.json`, `test_effect.json` |

No deviation from the frozen protocol.

### Commands

```bash
.venv/bin/python src/exp106_prior_correction_production.py --smoke
.venv/bin/python src/exp106_prior_correction_production.py --all
.venv/bin/python src/exp106_prior_correction_production.py --analyse
.venv/bin/python src/exp106_prior_correction_production.py --test-effect
```

## Results

| Seed | 2121 | 2122 | 2123 | 2124 | 2125 | Mean |
|---|---:|---:|---:|---:|---:|---:|
| Δ macro F1 (B25 − P) | +0.0022 | +0.0004 | −0.0010 | +0.0043 | −0.0008 | **+0.0010** |
| Verdict | NEAR-MISS | INCONCLUSIVE | INCONCLUSIVE | BETTER | INCONCLUSIVE | |

**Test-set effect:** 1 Task 1 prediction changes (`flow_000906` google → youtube), below the upload rule's minimum of 3.

## Verdict

**Not adopted: BETTER on 1 of 5 seeds; mean +0.001.** The prior correction that helped LLM_ops's weaker base (+0.006 in 103)
adds almost nothing to our production, whose facebook and instagram handling already corrects for rarity (Meta gate, verifiers,
rescues). Status: rejected. With 102-105, every allowed technique from the leaders' notes is now tested.
