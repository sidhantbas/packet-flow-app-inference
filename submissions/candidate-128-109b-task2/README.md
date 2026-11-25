---
title: "Candidate 128: upload 10 + 109 B in Task 2 (information only, not uploaded)"
created: 2026-10-21
creator: sidhantbas
description: "Upload 10's file with Task 2 from experiment 109's arm B (the facebook/instagram specialist on columns chosen by nested selection, here the decoded smallest upstream opening packet); one Task 2 test flow changes; built on request; not uploaded."
relation:
  - ../../experiments/128_109b_candidate.md
  - ../../experiments/109_task2_first_packet_specialist.md
  - ../../experiments/117_grouped_109b.md
  - ../candidate-127-meta-count-guided/README.md
---

# Candidate 128: upload 10 + 109 B in Task 2

**Status: built 2026-10-21 on the user's request; uploaded by Sid the same day (upload 11): about 87 (upload 10: 90.85). The
score is information only; upload 10 stays the displayed entry; nothing is built from this result.** Built by
`.venv/bin/python src/exp128_109b_candidate.py`.

## What changes

Task 1 is upload 10 (candidate 127) unchanged. Task 2 is experiment 109's arm B fitted on all 330 labelled Task 2 flows: the
production Task 2 model, with its facebook/instagram calls re-decided by a specialist whose columns are chosen by nested forward
selection. On the full data it chose one column, **`s_up_min`** (the smallest upstream packet of the opening, decoded from the
Task 2 summary columns by 090). One Task 2 test prediction changes, the same one 109 reported:

| Flow | Upload 10, Task 2 | This file, Task 2 | Upload 10, Task 1 |
|---|---|---|---|
| `flow_001187` | instagram | **facebook** | instagram (switched by 127) |

## Before any upload

- **Evidence:** the best facebook/instagram evidence we have (109: +0.020 on 5 of 5 never-used seeds, BETTER on 3 of 5; 117:
  survives grouped folds, +0.031, BETTER 5 of 5), but the frozen 5-of-5 rule was not met, and 117 found it rests on a two-value
  size rule.
- **Upload rule:** 1 changed prediction against upload 10 (needs 3): **does not qualify.** A one-flow file is a coin flip that
  reveals a test label.
- **Condition 3:** the decoded opening sizes may partly reflect the server name's length (114); Sid and Charles must decide first.
- **Cross-task conflict:** the same flow is instagram in Task 1 and facebook here; at most one is right. Task 2 may not use Task 1's
  answer (condition 2), so the conflict cannot be resolved by copying.

## Files

| File | SHA-256 |
|---|---|
| `submission.json` | `8c9001861fe71a6181d360c194c7f463558b2aa341b9e585b0acde9c9a40bd34` |
| `submission.zip` | `3d18c5d6b24277c083fc0e83befb5cbfec3ee6e3ae86018a2f8eb0cfbe03a549` |
| `comparison.json` | the change, counts, differences from every upload |
