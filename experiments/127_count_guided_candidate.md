---
title: "127: Count-guided Meta candidate file (information only)"
created: 2026-10-21
creator: sidhantbas
description: "Builds, on the user's request, a submission file where Task 1's instagram count is raised to the training mix's expectation by experiment 099's rule D; records its test changes and the cross-validation evidence against it; not uploaded."
source:
  - 099_class_count_deficit.md
  - 126_task1_meta_leak_rescue.md
experiment:
  id: '127'
  tasks: [task1]
  lever: decision
  status: tooling
  verdict: 'Candidate file: 099 rule D moves 3 Task 1 test flows to instagram (flow_000223 and flow_001187 from facebook, flow_001003 from google); CV evidence negative (flips right 27%, Δ −0.0169), so it failed the upload rule; uploaded by Sid anyway (upload 10): 90.85, our best score, Task 1 ≈ 0.912; information about the test set, not evidence for the rule'
---

# 127: Count-guided Meta candidate file

**Status: done 2026-10-21; uploaded by Sid as upload 10: 90.85.** Sid, 2026-10-21: "build the submission file in json format, and put the instagram and facebook flow
order accordingly, on your own instinct". **No new measurement:** the rule is experiment 099's pre-registered rule D, already
measured in cross-validation; this records the file it produces.

## Rule

Fixed before building, written into `src/exp127_count_guided_candidate.py`: start from the production file (100 + 014); in Task 1,
E = round(81 × instagram share of the 330 labelled flows) = 5, production calls 2 test flows instagram, so k = 3; the k test flows
production does not call instagram with the highest instagram score (099's saved three-expert mean) become instagram. Task 2 is
unchanged. No test labels, test `label_counts` or leaderboard scores are used.

## Result

File: [`submissions/candidate-127-meta-count-guided/`](../submissions/candidate-127-meta-count-guided/README.md).

| Flow | Production | Candidate | Instagram score |
|---|---|---|---:|
| `flow_000223` | facebook | instagram | 0.427 |
| `flow_001187` | facebook | instagram | 0.292 |
| `flow_001003` | google | instagram | 0.184 |

Differences from earlier uploads (Task 1 / Task 2): upload 1 11/0, 2 8/0, 3 5/0, 4 4/0, 5 5/0, 6 5/0, 7 3/0, 8 3/0, 9 5/0.

## Verdict

**Built, not uploadable.** The file meets the "≥ 3 changes" half of the upload rule but not the "rule v2 on never-used seeds" half:
in 099, rule D's flips were right 27% of the time and cost Δ −0.0169 macro F1 (about −0.85 points). 126 explains why: the instagram
flows Task 1 misses are light and look like other apps, so the most instagram-like remaining flows are mostly not instagram.

## Upload (after this log was written)

Sid uploaded the file the same day (upload 10): **90.85**, +2.74 over 88.11 and +4.49 over upload 8 (the same base file without the
three changes). Leaderboard row ([raw](../submissions/raw/leaderboard-final-test-2026-10-21.txt)): Task 1 **45.60 points (macro F1 0.912)**, accuracy
0.90; Task 2 45.25 (0.905), accuracy 0.89; now the displayed entry. Task 1 was 0.822 for upload 8.

**Reading, kept honest:**

1. **The test set behaved unlike cross-validation.** 099 had already found that Task 1's instagram deficit on the test set (2
   predicted where about 5 are expected) never occurred in 50 CV folds. A rule that restores the training mix's count can pay off on
   such a test set while losing on average in CV; three flows decide it.
2. **The score is information, not evidence for the rule.** It does not show that rule D works in general, and it reveals
   something about test labels. **Which of the three flows are right is not worked out from the scores, and no further files are
   built by varying these flips** (condition 1, never tuning toward the leaderboard).
3. **For the report:** the file is reproducible from `src/exp127_count_guided_candidate.py` and the production model; the count
   comes from the training mix (no test labels, no test `label_counts`); the negative CV and the upload decision are disclosed.
