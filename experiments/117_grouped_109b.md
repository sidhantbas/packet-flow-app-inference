---
title: "117: Does 109 B's Task 2 gain survive grouped (twin-aware) cross-validation?"
created: 2026-10-19
creator: sidhantbas
description: "Frozen robustness test of 109 B (Task 2 facebook/instagram specialist with columns chosen per fold, mostly the decoded first-packet size) against production 014 on grouped folds built from Task 2 openings only: exact-duplicate groups (primary) and near-duplicate groups at 0.05 (stress test), seeds 2166-2170."
source:
  - 109_task2_first_packet_specialist.md
  - 036_twin_aware.md
  - 115_identifiability_and_artefacts.md
experiment:
  id: '117'
  tasks: [task2]
  lever: evaluation
  status: measured
  verdict: '109 B survives grouping by the frozen rule: exact-duplicate groups Δ +0.031 ± 0.009, BETTER on 5 of 5 (near-0.05 stress +0.032, 5 of 5); top group 35% of the pooled gain. But it is a two-value rule (1365 B → facebook, 1367 B → instagram) resting on two near-identical facebook pairs; facebook F1 falls on grouped folds while instagram rises. Grouped folds also cut production Task 2 from about 0.76 to 0.48 macro F1: Task 2 skill is largely memorised openings. Not adoptable now.'
---

# 117: 109 B on grouped folds

**Status: done 2026-10-19. Protocol frozen (`fb0aade`) before any code or run.**
**Verdict: 109 B's gain survives grouped folds (robust by the frozen rule), but its mechanism is a two-value size rule resting on
very few facebook flows; not adoptable for the final submission.** Results are below the protocol.
Do not edit the frozen sections after execution starts. Sid, 2026-10-19 (audit follow-up): does 109 B's gain reflect transferable
signal, or near-duplicate capture examples? No production or submission change.

## Question and evidence

109 B (`SelectSpecialist`, `src/exp109_task2_first_packet_specialist.py`) beat production 014 on ordinary folds: +0.0197 mean
over seeds 2136-2140, Δ > 0 on 5 of 5, rule v2 BETTER on 3 of 5, facebook and instagram F1 about +0.06 each. Ordinary folds put
exact copies of an opening in training and validation at the same time (256 of 330 labelled flows have an identical 12-column
twin), so a specialist keyed on exact sizes could profit from copies rather than from app behaviour. Grouped folds keep copies
together.

## Grouping (decided from feature structure and class composition only, before any model result)

Groups are built from **Task 2 columns only** (`cv.no_timing_features`, 12 columns), log1p and standardised over the 330 labelled
flows (as 036 did for Task 1), Euclidean distance, connected components.

| Grouping | Groups | Largest (flows) | Test-fold size (seed 2166, 10 repeats) | Facebook / instagram per test fold |
|---|---|---|---|---|
| **Exact duplicates** (distance 0) | 123 (74 singletons) | 37, 26, 14 | 59-76 | 2-3 / ≥ 3 |
| Near duplicates (≤ 0.05) | 55 | **80** (google 55 + youtube 25), 45, 27 | 48-94 | 2-3 / ≥ **1** |

At 0.05 chaining forms an 80-flow component larger than one test fold, and instagram falls into 6 groups (as few as 1 instagram flow
in a test fold). **Primary: exact-duplicate grouping. Stress test: near-duplicate grouping at 0.05**, reported with that limitation.

## Frozen design

- **Arms:** P2 = production `models.task2_model` (014) on the 12 production columns; B = 109 B (`SelectSpecialist` on 109's 30
  candidates: 12 production + 10 engineered + 8 decoded sizes; nested forward selection inside each training fold).
- **Folds:** `StratifiedGroupKFold(5, shuffle=True, random_state = seed + repeat)`, 10 repeats, seeds **2166-2170** (0 runs in
  `results/`), for each grouping; both arms receive the identical split list; model seed = fold index.
- **Smoke check:** no group in both training and validation of any fold; both arms' folds identical; P2 on one grouped fold equals
  `task2_model` fitted directly.
- **Reported per seed and grouping:** macro F1 of both arms, paired Δ = B − P2 (rule v2 verdict), per-class precision / recall / F1,
  facebook / instagram / google confusion counts, distinct flows misclassified (at least once and in most repeats), changed
  predictions and the distinct flows and groups behind them, training and validation class counts per fold (min / max), group
  sizes and class composition. Mean and standard deviation of Δ over the 5 seeds, next to 109's ordinary-fold result.

## Decision rule

- **Robust:** on the primary (exact) grouping, Δ > 0 on all 5 seeds and no seed rule v2 WORSE; and no single group accounts for
  more than half of B's net gain in flows.
- **Artefact:** Δ ≤ 0 on at least 3 of 5 primary seeds.
- **Otherwise:** inconclusive.
- The stress test is reported but does not override the primary reading.
- Either way this is evidence only. Adoption needs the user's decision and the condition 3 decision on the decoded first-packet
  size; an upload also needs the upload rule (109 B changes 1 Task 2 test prediction against the submitted file).

## Boundaries

Task 2 reads only `task2_realtime_prefix5/` files (groups included). Train + validation labels only; no test data at all. No
production or submission change.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-19 | Grouping structure inspected (features and labels only, no model results) | table above |
| 2026-10-19 | Protocol frozen and committed | before any code change or run |
| 2026-10-19 | Runner committed (`5661cfc`); smoke and fold integrity | 0 groups in both training and validation over all 500 folds; split lists deterministic and identical for both arms; P2's factory is `models.task2_model`. A first version of the smoke check compared a prediction with itself (vacuous); it was replaced before the runs |
| 2026-10-19 | 20 runs `…_117_<arm>_<grouping>_s<seed>` (`--all`) | every run read only Task 2 files (`data_sha256`) and both arms of each seed share a fold signature (asserted in `--analyse`) |
| 2026-10-19 | `--analyse`; pooled per-group and per-flow contributions | `117_evidence/results.json`, `group_contributions.json`, `selected_columns.jsonl` |

No deviation from the frozen protocol. "Net gain in flows" in the decision rule was computed as net fixed − broken predictions per
group (each flow is predicted 10 times per seed), pooled over the 5 seeds and also per seed.

## Results

Evidence: [`117_evidence/results.json`](117_evidence/results.json) (every seed, arm and class; integrity checks),
[`group_contributions.json`](117_evidence/group_contributions.json) (pooled gains by group and flow).

**Per seed** (macro F1 = mean of 50 grouped folds; Δ = B − P2; changed = predictions / distinct flows / distinct groups; last column
= largest single group's share of that seed's net gain):

| Grouping | Seed | P2 | B | Δ | Verdict (W/L/T) | facebook F1 | instagram F1 | google F1 | Changed | Top group |
|---|---|---:|---:|---:|---|---|---|---|---|---:|
| exact | 2166 | 0.4813 | 0.5062 | **+0.0249** | BETTER (21/7/22) | 0.32 → 0.25 | 0.59 → 0.73 | 0.67 → 0.67 | 113 / 24 / 12 | 0.5 |
| exact | 2167 | 0.4772 | 0.5227 | **+0.0455** | BETTER (28/3/19) | 0.30 → 0.28 | 0.58 → 0.76 | 0.66 → 0.66 | 118 / 23 / 11 | 0.261 |
| exact | 2168 | 0.4812 | 0.5083 | **+0.0271** | BETTER (21/6/23) | 0.32 → 0.26 | 0.59 → 0.75 | 0.66 → 0.66 | 126 / 24 / 12 | 0.417 |
| exact | 2169 | 0.4844 | 0.5077 | **+0.0233** | BETTER (19/5/26) | 0.34 → 0.26 | 0.59 → 0.74 | 0.67 → 0.67 | 113 / 20 / 9 | 0.714 |
| exact | 2170 | 0.4810 | 0.5134 | **+0.0324** | BETTER (21/7/22) | 0.33 → 0.29 | 0.58 → 0.74 | 0.66 → 0.66 | 116 / 22 / 10 | 0.375 |
| near | 2166 | 0.2390 | 0.2689 | **+0.0300** | BETTER (18/2/30) | 0.15 → 0.12 | 0.00 → 0.08 | 0.31 → 0.31 | 318 / 99 / 7 | 0.45 |
| near | 2167 | 0.2388 | 0.2678 | **+0.0290** | BETTER (16/2/32) | 0.15 → 0.11 | 0.00 → 0.08 | 0.32 → 0.32 | 311 / 99 / 7 | 0.389 |
| near | 2168 | 0.2359 | 0.2687 | **+0.0328** | BETTER (17/2/31) | 0.16 → 0.11 | 0.00 → 0.10 | 0.31 → 0.31 | 323 / 99 / 7 | 0.488 |
| near | 2169 | 0.2361 | 0.2674 | **+0.0313** | BETTER (16/1/33) | 0.16 → 0.11 | 0.00 → 0.10 | 0.33 → 0.33 | 321 / 99 / 7 | 0.488 |
| near | 2170 | 0.2367 | 0.2759 | **+0.0392** | BETTER (18/1/31) | 0.16 → 0.12 | 0.00 → 0.10 | 0.32 → 0.32 | 330 / 99 / 7 | 0.438 |

**Summary:** exact grouping Δ **+0.0306 ± 0.0090** (mean ± sd over 5 seeds), Δ > 0 on 5 of 5,
BETTER on 5, WORSE on 0; near grouping +0.0324 ± 0.0040, BETTER on 5 of 5.
Ordinary folds (109, seeds 2136-2140): +0.0197 mean, BETTER on 3 of 5.

**Where the exact-grouping gain comes from** (pooled over 5 seeds × 10 repeats; net = fixed − broken predictions = 66):

| Flow | App | First packet | Net |
|---|---|---:|---:|
| `flow_000799` | facebook | 1365 B | +23 |
| `flow_000379` | instagram | 1367 B | +22 |
| `flow_001145` | facebook | 1365 B | +20 |
| `flow_001185`, `flow_001321` | instagram | 1365 / 1367 B | +5 each |
| `flow_000368` | facebook | 1367 B | −5 |
| `flow_001168` | facebook | 1365 B | −3 |
| `flow_000024` | facebook | 150 B (TCP) | −2 |

The largest single group holds 35% of the pooled gain (all groups involved are single flows); per seed the largest share ranges
0.26-0.71 (0.71 on seed 2169). Three flows carry 98% of the net gain.

**Integrity:** groups built from the 12 Task 2 columns only; 0 groups in both training and validation over all 500 folds; both
arms of every seed share one fold signature; every run read only Task 2 files; feature selection inside each training fold
(`SelectSpecialist.fit`); no test data read; training facebook 8-9 and validation facebook 2-3 flows per fold in both groupings;
validation instagram 3-4 (exact) and 1-8 (near).

## Verdict

**By the frozen rule, 109 B's gain is robust to grouping:** on exact-duplicate groups it is positive and rule v2 BETTER on all 5
seeds (Δ +0.031 ± 0.009, larger than on ordinary folds), no seed is WORSE, and no single group holds more than half the pooled gain.
The near-duplicate stress test agrees (+0.032, 5 of 5 BETTER), within its stated limitation.

**What the evidence actually supports is narrower:**

1. **The mechanism is a two-value lookup on the decoded first-packet size:** 1365 B → facebook, 1367 B → instagram. It fixes the
   facebook flows at 1365 B and the instagram flows at 1367 B, and breaks the facebook flows that sit at 1367 B (`flow_000368`,
   `flow_000617`). That is the class-conditional majority of each value (1365 B: facebook 4, instagram 1, google 30; 1367 B:
   instagram 16, facebook 3), applied only after the base model has called a flow Meta.
2. **Its facebook evidence is about two independent observations.** The four facebook flows at 1365 B are two near-identical pairs
   (090); exact-duplicate grouping does not keep near-identical pairs together, and near grouping holds each pair together but
   leaves the other pair in training. Three flows carry 98% of the net gain.
3. **Facebook F1 falls on grouped folds** (about 0.32 → 0.26 on every exact seed); the macro gain comes from instagram (about 0.59 →
   0.74). Google is unchanged.

**A second, larger finding: Task 2's skill is largely memorised openings.** Production's Task 2 macro F1 is about 0.76 on ordinary
folds, **0.48** when exact copies of an opening are kept in one fold, and 0.24 with near-duplicate groups (instagram F1 0.00: its
flows sit in 6 near-duplicate groups). Since 63% of test flows have an exact single-label twin in the labelled data (115), this
explains why our Task 2 test score (0.905) is far above its cross-validation level (0.754).

**Recommendation: do not adopt 109 B for the final submission; report it.** It survives grouping, but its gain is a value lookup
resting on two facebook pairs, it lowers facebook F1 on grouped folds, the condition 3 question on the decoded size is open, and it
changes one Task 2 test prediction (below the upload rule's three). It belongs in the technical report as a finding about the
dataset (a size value that separates the two Meta apps in this capture), together with the memorisation result.
