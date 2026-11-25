---
title: "078: TabPFN v2 as an extra expert in the current Task 1 production model (check only)"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for re-testing the local TabPFN v2 model (024) as a third expert inside the Meta-gate model; run at the user's request to see the result before any decision on the pretrained-model rule.
source:
  - 024_tabpfn.md
  - 065_task1_rest_expert.md
  - 077_fingerprint_expert.md
experiment:
  id: 078
  tasks:
  - task1
  lever: model
  status: inconclusive
  verdict: 'TabPFN as an extra expert (check only): mean +0.0027, no seed BETTER; pretrained, excluded'
---

# 078: TabPFN v2 as an extra expert in the current Task 1 production model (check only)

**Status: done 2026-10-09 (check only). Protocol frozen (`6ea1930`) before any code change or run.**
**Result: +0.0027 mean over five seeds (54% of non-tied folds), no seed BETTER; fails rule v2 and the 066 criteria. The 024 gain is mostly absorbed by the current model. The pretrained-model rule stays as it is.** Results are below.
Do not edit the frozen sections after execution starts.

## Rule status (read first)

Team rule since 2026-10-01 (AGENTS.md) and `.mission.md` OUT OF SCOPE: **no pretrained models**. User request 2026-10-09:
"can we just check it out, what the result it gives and then we can figure out everything later". This run is therefore a
**check only**: it changes nothing in production or in any submission. Using TabPFN in production or a submission needs the
user to lift the rule first (and a report disclosure, challenge rule 4). Only the local `tabpfn` package is used
(9.0.0, model version v2, ungated weights cached in `~/Library/Caches/tabpfn`, CPU); `tabpfn-client` (uploads data) is never used.
No data leaves this Mac.

## Evidence before this experiment

[024](024_tabpfn.md) (2026-09-30): TabPFN as a third member of the then Task 1 model (022), 1/3 weight, facebook kept:
+0.014 to +0.018 on all five seeds (BETTER on 2026, 2027, 2030; NEAR-MISS on 2028, 2029). TabPFN alone: Task 1 0.769.

## Frozen method

Production MetaGate (`models.task1_meta_gate`, the 34 production columns, unchanged experts and gate) with one extra expert,
`models.tabpfn` (TabPFN v2, `random_state` = model seed) on the same 34 columns. In `MetaGate.predict`,
`p = (pw + po + p_tabpfn) / 3`; all later rules unchanged.

## Frozen decision rules (for the record; adoption is not decided here)

- cv_seeds 2026-2030 vs production on the same seed (`20261001T173854Z_034_meta_gate`, `20261009T172902Z_062_production_s2027`,
  `…173025Z…s2028`, `…173146Z…s2029`, `…173307Z…s2030`).
- **Rule v2 pass:** BETTER on 2026, 2027 and 2028 (an a-priori idea from 024, not chosen from today's results).
- Also reported: the 066 exception criteria (Δ > 0 on all five, mean ≥ +0.004, pooled wins ≥ 62%, facebook mean ≥ 0),
  per-class Δ, and flow-level checks.
- Whatever the result, nothing changes until the user decides about the pretrained-model rule.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `6ea1930`, before any code change or run |
| 2026-10-09 | Runner committed; smoke test on one split | `2b37699`; one fit + predict 6.2 s; 4 of 165 predictions change, none touching Meta |
| 20:57-21:01 | cv_seeds 2026-2030 vs production | runs `20261009T205731Z_078_TP`, `…205825Z…_s2027`, `…205919Z…_s2028`, `…210014Z…_s2029`, `…210108Z…_s2030` |

No deviation from the frozen protocol. TabPFN ran locally on CPU; no data left the machine.

## Results (vs production on the same seed)

| Seed | Δ macro F1 | Wins / losses / ties | Verdict | facebook | google | mozilla | x | youtube |
|---|---:|---|---|---:|---:|---:|---:|---:|
| 2026 | +0.0015 | 23 / 18 / 9 | INCONCLUSIVE | −0.004 | −0.005 | +0.011 | +0.011 | −0.004 |
| 2027 | −0.0004 | 15 / 22 / 13 | INCONCLUSIVE | +0.000 | −0.011 | +0.011 | +0.009 | −0.012 |
| 2028 | +0.0034 | 22 / 20 / 8 | INCONCLUSIVE | +0.000 | −0.006 | +0.016 | +0.012 | −0.002 |
| 2029 | +0.0040 | 25 / 16 / 9 | NEAR-MISS | +0.004 | −0.001 | +0.005 | +0.013 | +0.003 |
| 2030 | +0.0048 | 23 / 16 / 11 | INCONCLUSIVE | +0.002 | −0.000 | +0.012 | +0.010 | +0.005 |

Mean +0.0027; pooled non-tied wins 108 / 200 = 54%; facebook mean +0.0004.

| Criterion | Holds |
|---|---|
| Rule v2: BETTER on 2026, 2027, 2028 | ❌ (no seed BETTER) |
| 066: Δ > 0 on all five | ❌ (2027 −0.0004) |
| 066: mean ≥ +0.004 | ❌ (+0.0027) |
| 066: pooled wins ≥ 62% | ❌ (54%) |
| 066: facebook mean ≥ 0 | ✅ (+0.0004) |

## Interpretation

In 024 TabPFN's gain on top of the 022 model came mainly from facebook (+0.054) and mozilla. The current model (034 Meta gate)
already captures the facebook part; what remains is a gain on mozilla and x offset by losses on google and youtube.

## Decision

Check only: no change. TabPFN would not justify lifting the "no pretrained models" rule; the rule and `.mission.md` stay as they
are. Nothing to disclose, since nothing is used in production or a submission.
