---
title: "Candidate 127: count-guided Meta file (information only, not uploaded)"
created: 2026-10-21
creator: sidhantbas
description: "Production file with Task 1's instagram count raised to the training mix's expectation (5 of 81) by switching the three most instagram-like flows; built on request; uploaded as upload 10 (90.85) although cross-validation says the rule loses."
relation:
  - ../../experiments/127_count_guided_candidate.md
  - ../../experiments/099_class_count_deficit.md
  - ../production-100-cross-task/README.md
---

# Candidate 127: count-guided Meta file

**Status: built 2026-10-21 on the user's request; uploaded by Sid the same day (upload 10): 90.85 (Task 1 macro F1 0.912 / accuracy
0.90, Task 2 0.905 / 0.89; [leaderboard row](../raw/leaderboard-final-test-2026-10-21.txt)), our best score and the displayed entry.** The score is information about the test set; the rule behind the file still failed cross-validation. Built by
`.venv/bin/python src/exp127_count_guided_candidate.py` from the production file
([`production-100-cross-task/`](../production-100-cross-task/)).

## What changes

Task 1 predicts 2 instagram flows where the training mix expects 5 (19 of 330 labelled flows are instagram; 81 × 19/330 = 4.7). The
three test flows production does not call instagram with the highest instagram score (experiment 099's three-expert mean) become
instagram. Task 2 is unchanged (production 014).

| Flow | Production | This file | Instagram score |
|---|---|---|---:|
| `flow_000223` | facebook | instagram | 0.427 |
| `flow_001187` | facebook | instagram | 0.292 |
| `flow_001003` | google | instagram | 0.184 |

Task 1 counts after the change: google 32, x 20, youtube 13, mozilla 9, instagram 5, facebook 2.

## Evidence and upload status

- **Cross-validation says the rule loses:** 099 rule D (cv_seed 2026) switched 44 flows, 12 of them correctly (27%); paired Δ
  macro F1 −0.0169 (7 W / 20 L / 23 T), about −0.85 leaderboard points if the test behaves like CV.
- **Upload rule:** differs from every earlier upload in at least 3 Task 1 predictions (3 vs uploads 7 and 8, 5 vs the displayed
  entry 9), but the rule behind it has **not** passed rule v2 on never-used seeds, so it does not qualify.
- `flow_000223` is the flow upload 8 changed (youtube → facebook, −0.87 points). That score was not used to build this file, in
  either direction (never tune toward the leaderboard).

## Files

| File | SHA-256 |
|---|---|
| `submission.json` | `1ee9da4ee670d779e9902d464e65a8e90854a45e70749351f305fdeb1c308442` |
| `submission.zip` | `78df6c79402a7dc56e66449d2575b25f21fe9630238458b6cfb5d3205dcc6240` |
| `comparison.json` | flips, counts, differences from every upload |
