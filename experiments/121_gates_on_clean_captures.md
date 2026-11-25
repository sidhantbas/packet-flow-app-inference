---
title: "121: Do our captures pass the capture gates after the clean re-extraction?"
created: 2026-10-19
creator: sidhantbas
description: "Frozen re-run of capture gates 1 and 2 (src/capture_checks.py, unchanged) on the clean extraction (120: process-attributed labels, background removed, edges trimmed) against the original extraction, per capture group and combined; decides whether a capture training test may follow."
source:
  - 120_capture_clean_extraction.md
  - 052_iphone_pilot.md
  - 055_long_sessions.md
  - 059_android_signature.md
  - 056_capture_augmentation.md
experiment:
  id: '121'
  tasks: [task1]
  lever: data
  status: measured
  verdict: 'The clean extraction still fails gate 2 everywhere: adversarial AUC 0.947 → 0.945 (all), 0.960 → 0.964 (iPhone, process labels); captured facebook and instagram flows sit nearest to challenge google flows. The preprocessing was not the cause: packet sizes and counts alone separate captures from challenge flows (AUC 0.923, post hoc). Capture training stays closed'
---

# 121: Capture gates on the clean extraction

**Status: done 2026-10-19. Protocol frozen (`d9926c7`) before any code or run.**
**Verdict: the cleaned captures fail gate 2 exactly as before; the preprocessing was not what made them unusable.** Results are
below the protocol.
Do not edit the frozen sections after execution starts. Sid, 2026-10-19: Charles called our capture data unusable because the
preprocessing was not done properly; re-run the test on the attributed data. **Measurement only:** no training, no model change.

## Question

The captures failed gate 2 in every group (052, 055, 059: adversarial AUC 0.88-0.99). Was that failure caused by our preprocessing
(session labels, background traffic, edge flows), which 120 removed, or by the captures themselves (device, app version, flow
cutting)?

## Frozen design

Gate functions `gate1`, `gate2` and `opening_report` from `src/capture_checks.py` are called **unchanged** (same columns, scaling,
thresholds: per app, median nearest-neighbour distance ≤ the originals' 90th percentile and same-label 5-NN share ≥ the originals';
adversarial AUC ≤ 0.70 with at least 30 captured flows).

| Version | Flows | Labels |
|---|---|---|
| **V1** | first extraction (`data/captures/<group>/<session>/`), all flows | session labels |
| **V2** | clean extraction (`data/captures/clean-v2/`), `keep = True` only | iPhone: process labels; Android: session labels (uncertain) |
| **V2-process** | V2, iPhone groups only | process labels only |

Each version is run per group (iPhone pilot, iPhone long, Android) and on all groups combined. Same sessions in every version
(those with flows in both extractions).

## Decision rule

- **If V2 or V2-process passes gates 1 and 2 combined** (the project's precondition for training use), a capture training test may
  follow under its own frozen protocol and the user's decision (Task 1 only).
- **If both fail gate 2**, the preprocessing was not the cause; capture training stays closed. The change in adversarial AUC and
  distances from V1 to V2 measures how much the cleaning moved the captures towards the challenge data.

## Boundaries

Train + validation features and labels of the original data only (as `capture_checks.py`); no test data. Captures are compared,
never trained on.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-19 | Protocol frozen and committed | before any code change or run |
| 2026-10-19 | `src/exp121_gates_clean.py` run (14 s) | `121_evidence/gates_<version>_<scope>.txt`, `summary.json` |
| 2026-10-19 | **Post hoc** (not in the protocol): adversarial AUC per feature family on V2 (all groups) | `121_evidence/post_hoc_auc_by_family.json` |

No deviation from the frozen protocol. V2-process equals V2 on the iPhone groups (their V2 labels are already process labels).

## Results

Gate printouts: `121_evidence/gates_*.txt`; summary: [`summary.json`](121_evidence/summary.json). Per-app cells: median distance to
the nearest original flow / same-label share among the 5 nearest original flows. The originals' thresholds: distance 90th
percentile facebook 2.15, instagram 2.01, youtube 1.25; same-label share facebook 0.16, instagram 0.41, youtube 0.59.

| Version / scope | Flows | Gate 1 | Gate 2 | Adversarial AUC (≤ 0.70) | facebook | instagram | youtube |
|---|---:|---|---|---:|---|---|---|
| V1 / iphone_pilot | 272 | PASS | **FAIL** | 0.986 | 1.94 / 0.01 | 2.11 / 0.11 | 1.42 / 0.31 |
| V1 / iphone_long | 270 | FAIL | **FAIL** | 0.957 | 0.84 / 0.02 | 1.23 / 0.13 | 1.19 / 0.28 |
| V1 / android | 119 | PASS | **FAIL** | 0.903 | 1.35 / 0.06 | 1.32 / 0.09 | — |
| V1 / all | 661 | FAIL | **FAIL** | 0.947 | 1.44 / 0.04 | 1.75 / 0.11 | 1.20 / 0.29 |
| V1 / iphone_all | 542 | FAIL | **FAIL** | 0.960 | 1.52 / 0.02 | 1.88 / 0.12 | 1.20 / 0.29 |
| V2 / iphone_pilot | 143 | PASS | **FAIL** | 0.986 | 1.56 / 0.01 | 2.19 / 0.12 | 1.63 / 0.27 |
| V2 / iphone_long | 195 | FAIL | **FAIL** | 0.969 | 0.87 / 0.02 | 1.22 / 0.15 | 1.23 / 0.25 |
| V2 / android | 100 | PASS | **FAIL** | 0.902 | 1.25 / 0.05 | 1.32 / 0.04 | — |
| V2 / all | 438 | FAIL | **FAIL** | 0.945 | 1.27 / 0.04 | 1.82 / 0.10 | 1.24 / 0.25 |
| V2 / iphone_all | 338 | FAIL | **FAIL** | 0.964 | 1.37 / 0.02 | 2.11 / 0.12 | 1.24 / 0.25 |
| V2-process / iphone_all | 338 | FAIL | **FAIL** | 0.964 | 1.37 / 0.02 | 2.11 / 0.12 | 1.24 / 0.25 |

- **Distances are mostly within range; labels are not.** Captured flows sit about as close to original flows as originals sit to each
  other, but their nearest original flows belong to other apps: same-label share facebook 0.02 (originals 0.16), instagram 0.10-0.15
  (0.41), youtube 0.25 (0.59).
- **Label discovery (V2, all groups):** the nearest original flow of a captured facebook flow is google 45, x 17, youtube 10,
  facebook 9 times; of a captured instagram flow google 77, x 42, mozilla 15, youtube 13, facebook 9, instagram 4 times.
- **Gate 1** fails only in the long cellular group: 2 of 195 downstream frames exceed 1514 B there (merged segments; both
  extractions used the first extraction's settings, which did not split merged segments for that group).
- **Post hoc, what separates captures from challenge flows** (adversarial AUC by feature family, V2 all groups): sizes and counts
  without timing **0.923**; timing only 0.862; `min_iat` alone 0.635 (`min_iat` = 0 in 98% of original flows vs 70% of captured);
  all 17 columns 0.960.

## Verdict

**The cleaned captures fail gate 2 in every group and combined, as the original extraction did; capture training stays closed.**

1. **The preprocessing was not the cause.** Process attribution, background removal and edge trimming changed the adversarial AUC by
   −0.002 (all groups) and +0.004 (iPhone). The captures remain about 95% distinguishable from the challenge flows.
2. **What makes them different is what the phones sent.** Packet sizes and counts alone separate the two (AUC 0.923); timing adds
   little, and the timestamp-resolution difference explains little (0.635). The remaining clean-up steps (flow cutting, timestamp
   resolution, retransmissions) act mainly on timing, so they cannot close a gap that sits in the sizes: our phones' QUIC first
   packets are 1242-1294 B, the challenge's 1363-1393 B (055, 059, 114), a device and app-version difference.
3. **The label check is the sharpest symptom:** a captured facebook or instagram flow's nearest challenge flow is usually a
   **google** flow. That is the fingerprint mismatch (115) seen from the capture side.

**For Charles:** the preprocessing did have flaws (session labels, background traffic, edge flows, two merged segments), and they are
now fixed and documented (120). Fixing them does not change the outcome: the captures differ from the challenge data at the packet
level, because they come from different devices and app versions.
