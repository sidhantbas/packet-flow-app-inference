---
title: "076: Screening new views of each flow for complementarity with production (measurement only)"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Pre-defined candidate views built from relations between released columns, each scored alone and by how many production errors it fixes versus correct predictions it breaks; the best view goes to a separate frozen test.
source:
  - 028_two_clerks.md
  - 065_task1_rest_expert.md
  - 070_largest_up_packet_bounds.md
  - 039_capture_order.md
experiment:
  id: '076'
  tasks:
  - task1
  lever: diagnostic
  status: measured
  verdict: 'View screen: the opening fingerprint fixes 51% more production errors than the opening view at equal breaks'
---

# 076: Screening new views for complementarity with production (measurement only)

**Status: done 2026-10-09. Definition frozen (`1cf5184`) before any run.**
**Result: V3 (opening fingerprint) has the best fixes-to-breaks balance (0.44) at the opening's standalone level; it goes to 077.** Results are below.
User request 2026-10-09: find another new view like the opening; work on the data-distribution side efficiently.

## Why this shape

The opening (022, 028) helped because it carried information the whole-flow totals blur, and its errors differed from
production's. A screen measures exactly that for each candidate view before any full test. Capture time and order
(`start_rel`, `flow_id`) stay excluded (039); Task 2 views use only Task 2 columns.

## Frozen candidate views (Task 1; built from `cv.task1_prefix_rest_features`)

| View | Columns |
|---|---|
| V1 rest-of-flow (reference, 065) | the 11 `r_*` columns |
| V2 cross-view shape | opening share of bytes up, bytes down, packets and duration (p5 / whole, 0 when the whole is 0); mean up size and mean down size of the opening minus those of the rest; opening up/down packet ratio minus the rest's; `transport` |
| V3 opening fingerprint | per direction: largest-packet bounds (070 formula, up and down), smallest-packet bounds (m − s·√(n−1), m − s/√(n−1); exact when n = 2), "all packets equal" flag, packet count; `transport` |
| V4 timing only | duration, mean / std / min / max iat, burst_count (whole flow) |
| V5 size only | packet counts, bytes, mean and std packet size per direction, both ratios (whole flow), `transport` |

## Frozen measurements (cv_seed 2026, same folds as production `20261001T173854Z_034_meta_gate`)

For each view, a balanced `models.SoftVote` on the view's columns only, recorded with `runlog.record_run` (no reference):

1. standalone macro F1;
2. **fixes**: production's wrong held-out predictions that the view gets right (count and share);
3. **breaks**: production's right held-out predictions that the view gets wrong (count and share);
4. fixes on facebook/instagram and on google/youtube separately.

Reference point: the opening expert (028's 12 prefix columns) measured the same way.

## Use of the result

Measurement only. The view with the best fixes-to-breaks balance (and a standalone macro F1 not far below the opening
expert's) is tested next as a separate expert inside production, with its own frozen protocol and the five-seed rule. Since
it is chosen after this screen, that test requires BETTER on all five seeds.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Definition frozen and committed | `1cf5184`, before any run |
| 20:07 | Screen script (`2b3d6e4`) run: six SoftVote runs on cv_seed 2026 | runs `results/*_076_V*`; table `experiments/076_evidence/view_screen.csv` |

## Results (production: 412 wrong and 2,888 right held-out predictions over 10 repeats)

| View | Columns | Macro F1 alone | Fixes (share of production errors) | Breaks (share of production rights) | Fix / break | Fixes on facebook/instagram | Fixes on google/youtube |
|---|---:|---:|---|---|---:|---:|---:|
| V0 opening (reference) | 12 | 0.7362 | 49 (11.9%) | 161 (5.6%) | 0.30 | 12 | 37 |
| **V3 opening fingerprint** | 13 | **0.7347** | **74 (18.0%)** | 167 (5.8%) | **0.44** | **19** | 51 |
| V1 rest-of-flow | 11 | 0.7056 | 161 (39.1%) | 501 (17.3%) | 0.32 | 6 | 114 |
| V2 cross-view shape | 8 | 0.6912 | 92 (22.3%) | 435 (15.1%) | 0.21 | 8 | 63 |
| V5 size only | 11 | 0.6545 | 126 (30.6%) | 480 (16.6%) | 0.26 | 1 | 97 |
| V4 timing only | 6 | 0.5770 | 127 (30.8%) | 928 (32.1%) | 0.14 | 9 | 95 |

## Reading

- V3 matches the opening view alone (0.735 vs 0.736) but disagrees with production more usefully: 51% more fixes (74 vs 49)
  for about the same breaks, and the most facebook/instagram fixes of any view. It is the opening rewritten as packet sizes
  (smallest and largest per direction, equal flag, count) instead of mean and spread.
- V1 (rest of flow) fixes many errors but breaks three times as many rights; its tested gain (065) was small. V2, V4 and V5
  break far more than they fix.

## Decision

V3 goes to [077](077_fingerprint_expert.md) as a separate expert, chosen after this screen, so BETTER on all five seeds is required.
