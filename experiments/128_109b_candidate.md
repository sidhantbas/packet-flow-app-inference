---
title: "128: Candidate file with 109 B in Task 2 (information only)"
created: 2026-10-21
creator: sidhantbas
description: "Builds, on the user's request, upload 10's file with Task 2 replaced by experiment 109's arm B fitted on all labelled Task 2 flows; one Task 2 test flow changes; not uploaded."
source:
  - 109_task2_first_packet_specialist.md
  - 117_grouped_109b.md
  - 127_count_guided_candidate.md
experiment:
  id: '128'
  tasks: [task2]
  lever: decision
  status: tooling
  verdict: 'Candidate file built (information only, not uploaded): 109 B in Task 2 on top of upload 10 changes 1 test flow (flow_001187 instagram → facebook, specialist column s_up_min), as 109 reported; fails the upload rule (1 change, BETTER on 3 of 5 seeds) and awaits the condition-3 decision on decoded sizes'
---

# 128: Candidate file with 109 B in Task 2

**Status: done 2026-10-21; uploaded by Sid the same day (upload 11): about 87, against 90.85 for upload 10. Upload 10 stays
the displayed entry; the score is information only and is not acted on (it reveals a test label).** Sid, 2026-10-21: "build the 109 B file", after I listed the remaining candidates (109 B
was the only one with positive cross-validation evidence for facebook/instagram). **No new measurement:** the model and its test
effect are experiment 109's.

## What was built

[`submissions/candidate-128-109b-task2/`](../submissions/candidate-128-109b-task2/README.md): Task 1 = upload 10 (127); Task 2 =
109 B (`SelectSpecialist`, seed 0) on 109's 30 Task 2 columns, fitted on the 330 labelled flows. Its nested selection chose
`s_up_min` on the full data. One Task 2 prediction changes against upload 10: `flow_001187` instagram → facebook, exactly 109's
recorded test effect (`109_evidence/test_effect.json`).

## Verdict

**Built, not uploadable:** 1 change against upload 10 (the upload rule needs 3), 109 B was BETTER on 3 of 5 fresh seeds (the frozen
rule needed 5), and the decoded sizes await the condition-3 decision. The same flow is instagram in upload 10's Task 1, so the two
files disagree on its app; neither task may borrow the other's answer for Task 2.
