---
title: '038: Audit for unused information; Task 2 outputs as a Task 1 signal'
created: 2026-10-05
creator: sidhantbas
experiment:
  id: 038
  tasks:
  - task1
  - task2
  lever: diagnostic
  status: measured
  verdict: 'Field audit: no unused signal left (only identifiers, capture time, a constant port and forbidden test counts); Task 2 outputs inside Task 1 hurt (-0.006 / -0.013)'
---
# 038: Audit for unused information; Task 2 outputs as a Task 1 signal

- **Date:** 2026-10-05
- **Command:** `.venv/bin/python src/exp038_task2_signal.py` (about 50 s); field inventory from the file headers.
- **Runs:** `results/*_038_*`

## 1. Field inventory (all released files)

Both task folders hold the same files: `train/validation/test_features.csv`, `train/validation_labels.csv`,
`sample_submission.csv`, `metadata.json`. Every features file has the same 21 columns.

| Field | Task 1 production | Task 2 production | Note |
|---|---|---|---|
| duration, mean_iat, std_iat, min_iat, max_iat | Task 1 file: yes; Task 2 file (`p5_` copies): yes, in the 34-column whole-flow model | **no** (dropped in 007) | Opening timing used only by Task 1 |
| transport, packet_count_up/down, bytes_up/down, mean_pkt_size_up/down, std_pkt_size_up/down, burst_count, up_down_packet_ratio, up_down_byte_ratio | Task 1 file + Task 2 file | Task 2 file | Core statistics |
| server_port | no | no | 443 in 409 of 411 flows (2 port-80 flows) |
| start_rel | no | no | Recording time; excluded on purpose (alone 0.51; adding it never helped) |
| flow_id | join key only | join key only | Identifier; its number alone scores 0.50 |
| split | no | no | Split marker |
| *_labels.csv (flow_id, app) | training only | training only | Identical across tasks |
| sample_submission.csv | format only | format only | |
| metadata.json | no | no | Task name, split fractions, seed, file names, label counts; **test label counts must not be used** (condition 1) |

Unused by both: server_port, start_rel, split, flow_id (as a feature), metadata.

## 2. Overlap between the tasks

The tasks describe **the same 411 flows**: identical flow_ids, split, start_rel, transport and server_port in train, validation
and test, and identical labels. The Task 2 file of a flow is its first five packets; Task 1 already reads it (022).

Held-out predictions, cv_seed 2026 (Task 1 production 034 vs Task 2 production 014, same folds): the tasks disagree on 248 of
3,300 (7.5%). When they disagree, Task 1 is right 148 times, Task 2 55, both wrong 45.

| True class | Disagreements | Task 1 right | Task 2 right | Recall Task 1 / Task 2 |
|---|---|---|---|---|
| facebook / instagram | 83 | 51 | 18 | facebook 0.718 / 0.418; instagram 0.753 / 0.753 |
| google / youtube | 112 | 45 | 37 | google 0.877 / 0.887; youtube 0.789 / 0.751 |

Submitted test labels differ between the tasks on 5 of 81 flows.

## 3. Task 2 outputs inside Task 1 (cv_seed 2026, vs production)

| Variant | Macro F1 | Δ | W / L / T | facebook | Notes |
|---|---|---|---|---|---|
| (a) one-hot Task 2 label as features (inner OOF for training rows) | 0.8215 | -0.0062 | 16 / 26 / 8 | -0.011 | instagram +0.020, youtube -0.022 |
| (b) tiebreaker (margin < 0.1, Task 2 label in the top two) | 0.8143 | -0.0134 | 15 / 26 / 9 | -0.012 | applied to 89 predictions |

Both worse; no confirmation run.

## 4. Rules

Using Task 2 files, or a model trained on them, for Task 1 predictions is allowed (condition 2 restricts only Task 1 data in Task
2) and is already disclosed for 022. Nothing here uses outside data, test labels or identifiers. Using `metadata.json` test label
counts would break condition 1; `start_rel` is allowed but excluded by our own leakage reasoning.

## Conclusion

No unused signal worth pursuing. The only unused fields are identifiers, recording time, a constant port and forbidden test
counts. Task 2's view is already inside Task 1 (its features since 022, its expert since 028), and its separate predictions are
right less often than Task 1's where they disagree.
