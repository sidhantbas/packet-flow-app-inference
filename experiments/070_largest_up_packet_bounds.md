---
title: "070: Bounds on the largest outgoing packet of the opening (google vs youtube)"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for two derived columns that recover the first-QUIC-packet fingerprint in mixed openings, tested in Task 1 and Task 2.
source:
  - 069_google_youtube_measurement.md
experiment:
  id: '070'
  tasks:
  - task1
  - task2
  lever: features
  status: rejected
  verdict: 'Bounds on the largest outgoing packet: youtube up on every seed but facebook/mozilla down; macro flat (+-0.004)'
---

# 070: Bounds on the largest outgoing packet of the opening

**Status: done 2026-10-09. Protocol frozen (`a2f0a1a`) before any code change or run.**
**Verdict: no arm passes (all nine runs within ±0.004). The columns help youtube as designed (Task 2 youtube F1 +0.017, 95% interval above zero) but cost facebook and, in Task 2, mozilla. Not adopted.** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: "yes freeze and run 070".

## Question

Do two columns that bound the largest outgoing packet of the first five packets help the models separate youtube from
google, where 069 found the first-QUIC-packet fingerprint hidden (mixed QUIC openings with 3-4 up packets, 32% of the
google ↔ youtube errors)?

## Frozen columns (pure arithmetic, nothing fitted)

From the first-5-packet up-direction count n, mean m and population std s of the same flow:

- `up_max_lo` = m + s / √(n − 1), `up_max_hi` = m + s · √(n − 1) for n ≥ 2 (Samuelson's inequality; both equal the exact
  largest packet when n = 2); = m when n = 1; = 0 when n = 0.

Task 1 computes them from its `p5_` columns (Task 2 file of the same flow, as production already does, 022). Task 2
computes them from its own columns only (condition 2).

## Frozen arms

| Arm | Task | Change from production |
|---|---|---|
| **T1A** | Task 1 | the two columns added to the feature table (they reach the whole-flow expert's all-column model and the Meta gate; the opening expert unchanged) |
| **T1B** | Task 1 | as T1A, and the two columns also added to the opening expert's columns |
| **T2A** | Task 2 | the two columns added to production's 12 no-timing columns (base model and facebook/instagram stage) |

## Frozen decision rules

- Every arm on cv_seeds 2026, 2027, 2028 against production of its task on the same seed.
  Task 1 references: `20261001T173854Z_034_meta_gate`, `20261009T172902Z_062_production_s2027`,
  `20261009T173025Z_062_production_s2028`. Task 2 references: `20260930T173836Z_014_fi_same_nocw`,
  `20260930T173928Z_014_fi_same_nocw_s2027`, `20260930T173952Z_014_fi_same_nocw_s2028` (production configuration).
- **Pass:** rule v2 BETTER on all three seeds. A pass is a submission candidate (user's approval needed).
- Evidence only: flow-level paired check for youtube and google (`src/flowcheck.py --apps youtube,google`), pooled over the
  three seeds; an interval crossing zero reads as unproven.

## Boundaries

Train+validation only; Task 2 reads only its own files. Production frozen at 5eb9a8b until the user approves.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `a2f0a1a`, before any code change or run |
| 2026-10-09 | Runner and generalised `src/flowcheck.py` (`--apps`, `--task`) committed | `e86e642`; bounds verified on 20,000 random openings (exact for n = 2); flowcheck of a run against itself gives zero |
| 18:45-18:46 | T1A, T1B, T2A on 2026, 2027, 2028 | runs `20261009T1845…_070_<arm>[_s<seed>]` (9 runs) |
| after the runs | youtube/google flow checks pooled over 3 seeds | `experiments/070_evidence/flowcheck_<arm>.md` |

No deviation from the frozen protocol.

## Results (each vs production of its task on the same seed)

| Arm | 2026 | 2027 | 2028 | Verdicts |
|---|---|---|---|---|
| T1A | −0.0040 (8/15) | +0.0006 (18/12) | +0.0005 (12/8) | INCONCLUSIVE, NEAR-MISS, NEAR-MISS |
| T1B | +0.0005 (20/14) | +0.0017 (22/15) | +0.0035 (18/9) | INCONCLUSIVE, INCONCLUSIVE, NEAR-MISS |
| T2A | −0.0002 (17/16) | +0.0003 (17/16) | −0.0021 (18/14) | INCONCLUSIVE ×3 |

Per-class Δ F1 (2026 / 2027 / 2028):

| Arm | youtube | google | facebook | mozilla |
|---|---|---|---|---|
| T1B | +0.014 / +0.003 / +0.014 | +0.006 / +0.003 / +0.004 | −0.024 / −0.003 / −0.008 | +0.002 / +0.001 / +0.003 |
| T2A | +0.021 / +0.015 / +0.017 | +0.003 / +0.006 / +0.004 | −0.019 / −0.011 / −0.013 | −0.012 / −0.011 / −0.012 |

Flow-level check (youtube/google, pooled over 3 seeds; evidence only):

| Arm | youtube F1 Δ [95% interval] | google F1 Δ [95% interval] | McNemar fixed / broken |
|---|---|---|---|
| T1A | −0.004 [−0.010, −0.000] worse | +0.000 [−0.001, +0.003] unproven | 0 / 1 |
| T1B | +0.010 [−0.000, +0.021] unproven | +0.004 [−0.001, +0.011] unproven | 0 / 1 |
| T2A | **+0.017 [+0.005, +0.034] better** | +0.004 [−0.003, +0.013] unproven | 1 / 0 |

## Interpretation

- The bounds carry real youtube-vs-google information: youtube improves on every seed in both tasks, and in Task 2 the
  flow-level interval for youtube lies above zero.
- Added as general columns, they also change splits for other classes: facebook loses in both tasks (−0.003 to −0.024)
  and mozilla in Task 2 (about −0.012), so macro F1 does not move.
- A use limited to the google-vs-youtube decision could keep the youtube gain without touching other classes. That idea
  was formed after seeing these results (post hoc) and would need its own protocol and the five-seed rule.

## Decision

Not adopted; production unchanged. Logged as unproven for macro F1, with a real but offset youtube effect.
