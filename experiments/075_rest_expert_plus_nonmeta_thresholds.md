---
title: "075: Rest-of-flow expert (065 R) combined with non-Meta F/2 thresholds (062)"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for combining the two Task 1 changes that were positive on all five seeds, judged by the 066 exception criteria plus a requirement to beat 065 R alone.
source:
  - 066_rest_expert_five_seeds.md
  - 065_task1_rest_expert.md
  - 062_task1_nonmeta_thresholds.md
experiment:
  id: '075'
  tasks:
  - task1
  lever: decision
  status: inconclusive
  verdict: 'Rest-of-flow expert + non-Meta thresholds: mean +0.0061 vs production but no gain over the rest-of-flow expert alone'
---

# 075: Rest-of-flow expert combined with non-Meta F/2 thresholds

**Status: done 2026-10-09. Protocol frozen (`ed5572a`) before any code change or run.**
**Verdict: criteria 1, 2, 4 hold; criterion 3 fails (pooled wins 61.9% < 62%) and criterion 5 fails (mean Δ vs 065 R −0.0004). Not a candidate; no submission.** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: wants another submission; this is the only
new candidate with a basis ("yes run 075").

## Why

Two Task 1 changes were positive on all five seeds without passing rule v2: 065 R (rest-of-flow expert, mean +0.0066; 066
criteria met; uploaded, about 86, information only) and 062 (F/2 thresholds among non-Meta apps, mean +0.0030). They act on
different parts of the model (new information vs the final non-Meta decision), so their gains may add up.

## Frozen method

Model: 065 arm R (`exp065_task1_rest_expert.RestExpertMetaGate`, features `cv.task1_prefix_rest_features`), with the 062
decision change: after `base = argmax(q)`, flows whose base label is not facebook/instagram are re-decided among the four
non-Meta classes by `argmax(q_c − t_c)`; later production rules unchanged. Thresholds t_c = F_c / 2, where F_c is the
per-class F1 of the **065 R model** on an inner 5-fold stratified CV of the training fold (shuffle, random_state = model
seed). Nothing searched.

## Frozen criteria (all must hold; cv_seeds 2026-2030)

Against production on the same seed (references: `20261001T173854Z_034_meta_gate`, `20261009T172902Z_062_production_s2027`,
`…173025Z…s2028`, `…173146Z…s2029`, `…173307Z…s2030`):

1. Δ > 0 on all five seeds.
2. Mean Δ ≥ +0.004.
3. Pooled non-tied fold wins ≥ 62%.
4. Facebook mean Δ F1 ≥ 0.

Against 065 R on the same seed (`20261009T175524Z_065_R`, `…175634Z…_s2027`, `…175651Z…_s2028`, `…175709Z…_s2029`,
`…175726Z…_s2030`):

5. Mean Δ over the five seeds > 0 (the combination must add something beyond 065 R).

**All five hold:** submission candidate; the file is built and checked, and before upload it is recorded that this file
becomes the ranked entry on CV evidence, whatever it scores. **Otherwise:** no submission; slots stay in reserve.

## Boundaries

Train+validation only; Task 1 may read Task 2 files (022, disclosed). Production frozen at 5eb9a8b until the user approves.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `ed5572a`, before any code change or run |
| 2026-10-09 | Runner committed; smoke test on one split | `8b4955c`; zero thresholds reproduce 065 R exactly; the thresholds change 2 of 165 predictions, none touching Meta |
| 19:00-19:07 | cv_seeds 2026-2030 vs production | runs `20261009T190029Z_075_RN2`, `…190150Z…_s2027`, `…190312Z…_s2028`, `…190434Z…_s2029`, `…190557Z…_s2030` |

No deviation from the frozen protocol.

## Results

| Seed | Δ vs production | Wins / losses / ties | Verdict | facebook Δ F1 | Δ vs 065 R (wins / losses) |
|---|---:|---|---|---:|---|
| 2026 | +0.0063 | 33 / 16 / 1 | NEAR-MISS | +0.000 | +0.0009 (10 / 9) |
| 2027 | +0.0030 | 22 / 22 / 6 | INCONCLUSIVE | −0.002 | −0.0021 (5 / 13), WORSE |
| 2028 | +0.0071 | 30 / 16 / 4 | NEAR-MISS | +0.007 | +0.0004 (10 / 8) |
| 2029 | +0.0082 | 32 / 15 / 3 | NEAR-MISS | +0.011 | −0.0015 (7 / 11) |
| 2030 | +0.0060 | 26 / 19 / 5 | INCONCLUSIVE | +0.015 | +0.0001 (11 / 10) |

| Criterion | Value | Holds |
|---|---|---|
| 1. Δ > 0 on all five seeds | +0.0030 to +0.0082 | ✅ |
| 2. Mean Δ ≥ +0.004 | +0.0061 | ✅ |
| 3. Pooled non-tied wins ≥ 62% | 143 / 231 = 61.9% | ❌ |
| 4. Facebook mean Δ F1 ≥ 0 | +0.0062 | ✅ |
| 5. Mean Δ vs 065 R > 0 | −0.0004 | ❌ |

## Interpretation

The non-Meta thresholds add nothing on top of the rest-of-flow expert: the combination tracks 065 R seed by seed (−0.0021 to
+0.0009) and is slightly below it on average. The gains of 062 and 065 overlap rather than add up, since both act on
google/youtube. The combination is effectively 066's model, which was already uploaded.

## Decision

Not a candidate (criteria 3 and 5 fail); no submission. Remaining Final Test Phase slots stay in reserve. Production unchanged.
