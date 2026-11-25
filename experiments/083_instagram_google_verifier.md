---
title: "083: Google-vs-instagram verifier for instagram calls"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for re-checking every production instagram call with a model trained only on google and instagram flows, to remove false instagram calls on google flows.
source:
  - 079_pipeline_audit.md
  - 072_instagram_youtube_measurement.md
  - 071_gy_specialist_bounds.md
experiment:
  id: 083
  tasks:
  - task1
  lever: hierarchy
  status: adopted
  verdict: 'Google-vs-instagram verifier for instagram calls: rule v2 BETTER on 3 seeds (+0.0016 to +0.0045); test file unchanged; part of 084'
  production: Google-vs-instagram verifier (via 084)
---

# 083: Google-vs-instagram verifier for instagram calls

**Status: done 2026-10-09. Protocol frozen (`811c34d`) before any code change or run.**
**Verdict: stage 1 gate passed; stage 2 rule v2 BETTER on 2026, 2027, 2028 (+0.0021 / +0.0045 / +0.0016). A pass; its test file is identical to the 87.77 file, so no upload. Adoption into production is the user's decision.** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: "try another method to improve the instagram score".

## Why this target

Instagram's errors (production CV, per repeat): instagram → facebook 2.6 (cross-label twins, 067), google → instagram 1.9 (false
instagram calls), instagram → youtube 1.4 (one-offs, 072). In 079 the google/instagram pair is separable in isolation (SoftVote
AUC 0.99), so the false instagram calls on google flows are the most plausibly fixable instagram loss. Earlier pair specialists
(013, 071) targeted google vs youtube (AUC 0.94) and did not help.

## Stage 1 (cv_seed 2026, production folds)

Verifier inside each training fold: balanced `models.SoftVote` (seed = fold index) on the google and instagram rows of the fold,
the 34 production columns. Every flow production calls **instagram** is re-decided by the verifier (google or instagram). No other
call changes.

Measured: instagram and google precision / recall / F1, macro F1 (mean over repeats), google → instagram errors removed, true
instagram flows turned into google.

**Gate to stage 2 (frozen):** macro F1 (mean over repeats) > production's **and** google → instagram errors removed ≥ 2 × true
instagram calls broken. Otherwise stop.

## Stage 2 (only if the gate passes)

Through `cv.evaluate` / `runlog` vs production on cv_seeds 2026, 2027, 2028 (champion and 062 production references). Pass: rule v2
BETTER on all three; evidence: instagram/google flow-level check. A pass is a submission candidate (user approval; ranked file
chosen on CV before any score).

## Boundaries

Train+validation only; no test features; nothing pretrained. Production frozen at 5eb9a8b until the user approves.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `811c34d`, before any code change or run |
| 2026-10-09 | Stage 1 run inline (50 folds of cv_seed 2026, 4 s) | gate passed |
| 2026-10-09 | Stage 2 runner committed; smoke test: changes only instagram calls, all to google | `959158a` |
| 21:54-21:55 | Stage 2 on cv_seeds 2026, 2027, 2028 | runs `20261009T215444Z_083_IGV`, `…215459Z…_s2027`, `…215515Z…_s2028` |
| after the runs | Flow check; candidate file built and compared with both uploads (test features only) | `experiments/083_evidence/`, `submissions/candidate-083-instagram-verifier/` |

No deviation from the frozen protocol.

## Stage 1 (cv_seed 2026, pooled)

| | Instagram P / R / F1 | Google F1 | Macro F1 (mean of repeats) |
|---|---|---:|---:|
| Production | 0.737 / 0.753 / 0.745 | 0.889 | 0.8323 |
| Verifier | 0.782 / 0.737 / 0.759 | 0.890 | 0.8348 |

15 calls changed over 10 repeats: 9 google → instagram errors removed, 3 true instagram calls broken, 3 other classes changed.
Gate: macro up and 9 ≥ 2 × 3: passed.

## Stage 2 (rule v2, vs production on the same seed)

| Seed | Δ macro F1 | Wins / losses / ties | Verdict | instagram | google |
|---|---:|---|---|---:|---:|
| 2026 | +0.0021 | 11 / 3 / 36 | BETTER | +0.011 | +0.002 |
| 2027 | +0.0045 | 14 / 3 / 33 | BETTER | +0.023 | +0.004 |
| 2028 | +0.0016 | 12 / 3 / 35 | BETTER | +0.011 | −0.001 |

Flow-level check (instagram/google, pooled over three seeds; evidence only): McNemar fixed 2 (google `flow_000240`,
`flow_000547`), broken 0 (p = 0.5); instagram F1 +0.018 [−0.008, +0.050], google +0.002 [−0.003, +0.008]: both unproven.

## Test file (test features only, no labels)

`submissions/candidate-083-instagram-verifier/` passes the official loader (81/81 per task). Its predictions are **identical to
the 87.77 file** in both tasks (and differ from the 066 file only in the three flows that separate the two uploads): the verifier
overturns none of production's instagram calls on the test flows.

## Interpretation and decision

First change of the day that passes rule v2: a small, consistent gain from removing false instagram calls on google flows, with
facebook and youtube untouched. It cannot move the leaderboard, because the test file is unchanged; no upload. Adopting it in
production (`models.TASK_MODELS`, `runs.py champion`) would keep the code aligned with the best-validated model; it needs the
user's approval.
