---
title: Submission files
created: 2026-10-09
modified: 2026-10-17
creator: sidhantbas
description: Index of every Final Test Phase submission file, its model, cross-validation evidence, leaderboard result and SHA-256.
---

# Submission files

`submission.json` / `submission.zip` in this folder are what `src/make_submission.py` writes for the current production
model (since 2026-10-12: Task 1 = 100 FB, Task 2 = 014; `submission.json` byte-identical to `production-100-cross-task/`).
**Ranked entry: ⭐ `production-100-cross-task/`** (upload 8, 2026-10-12), the output of the production model adopted before its
score (100 FB, a deliberate exception); it scored 86.36, information only. By the rule fixed before the upload it is the ranked
entry whatever it scored. Earlier ranked entries: `production-089-bundle/` (87.24), `best-88.11-production-084/` (88.11). Every uploaded or candidate file is also kept in its own folder below, so later builds never overwrite it.

**Which file is our ranked entry is decided by cross-validation, before a new score is seen; leaderboard scores are
recorded as information only (challenge condition 1).**

**Upload rule (AGENTS.md, user decision 2026-10-12):** upload only a file whose model passed rule v2 on never-used seeds and that
differs from every earlier upload in at least 3 test predictions. No current file meets it.

| Folder | Model | Task 1 CV | Uploaded | Final Test Phase result | `submission.zip` SHA-256 |
|---|---|---|---|---|---|
| [`best-87.77-frozen-5eb9a8b/`](best-87.77-frozen-5eb9a8b/) | Frozen production `5eb9a8b`: Task 1 = 034 Meta gate, Task 2 = 014 | 0.828 | 2026-10-09 (Sid) | **87.77** (Task 1 0.850, Task 2 0.905) | `da1fb60c…2462` |
| [`candidate-066-rest-expert/`](candidate-066-rest-expert/) | Task 1 = 034 + rest-of-flow expert (065 arm R, 066 five-seed check); Task 2 unchanged | 0.833 (mean Δ +0.0066 over 5 seeds) | 2026-10-09 (Sid) | about 86 (as reported by Sid) | `bc826eaa…c98c` |
| [`latest-077-fr-best-cv/`](latest-077-fr-best-cv/) | Task 1 = 034 + opening-fingerprint and rest-of-flow experts (077 FR: BETTER on 4 of 5 seeds, 76% wins; youtube and google better at flow level); Task 2 unchanged | mean Δ +0.0062 over 5 seeds | not uploaded (not needed) | **same predictions as the 87.77 file** (`submission.json` byte-identical) | `493a5b1b…002d` |
| [`candidate-083-instagram-verifier/`](candidate-083-instagram-verifier/) | Task 1 = production + google-vs-instagram verifier for instagram calls (083: rule v2 BETTER on 3 seeds); Task 2 unchanged | +0.0016 to +0.0045 | 2026-10-09 (Sid) | 87.77 (identical predictions to the 87.77 file) | `3b3b6c54…4c67` |
| [`production-089-bundle/`](production-089-bundle/) | Task 1 = 084 ALL + rest-of-flow expert (065 R) + instagram-protecting doorman (087) + scoped H1 (036) (089 B1: rule v2 BETTER on all 5 never-used seeds 2031-2035, mean +0.0141); Task 2 unchanged | mean Δ +0.0141 (fresh seeds) | 2026-10-10 (Sid) | 87.24 (Task 1 0.840, Task 2 0.905; 2 Task 1 changes vs 88.11) | `f84d9002…b004` |
| ⭐ [`production-100-cross-task/`](production-100-cross-task/) | Task 1 = 089 + cross-task Meta rescue (100 FB: Task 2 instagram and Task 1 non-Meta → facebook; Δ > 0 on all 10 fresh fold sets, BETTER on 1 of 5 ordinary and 5 of 5 twin-aware; adopted as a deliberate exception, user decision 2026-10-12); Task 2 unchanged | 0.857 (seed 2026; fresh-seed mean Δ +0.011) | 2026-10-12 (Sid) | 86.36 (Task 1 0.822, Task 2 0.905; 1 Task 1 change vs upload 7) | `02ea4690…53d7` |
| [`final-2026-10-12-089-014/`](final-2026-10-12-089-014/) | Final candidate (098): 089 + 014 rebuilt, validated, hashed | as production | **not uploaded (identical to `production-089-bundle/`)** | no score change possible | `3bb46530…7dcf` |
| [`best-88.11-production-084/`](best-88.11-production-084/) | Task 1 = production + 083 verifier + google-vs-x verifier for x calls (084 ALL: rule v2 BETTER on all 5 seeds, mean +0.0050); Task 2 unchanged | mean Δ +0.0050 over 5 seeds | 2026-10-09 (Sid); again 2026-10-16 (upload 9, uploader to confirm) | **88.11** (88.10775; 1 Task 1 change vs 87.77); upload 9 identical: Task 1 0.8571, Task 2 0.9051 | `7879c92a…5c7b` |
| [`candidate-127-meta-count-guided/`](candidate-127-meta-count-guided/README.md) | Production file + 099 rule D in Task 1: the 3 most instagram-like non-instagram test flows become instagram (instagram count 2 → 5, the training mix's expectation); Task 2 unchanged | rule's CV: Δ −0.0169 (099 D) | 2026-10-21 (Sid; upload 10) | **90.85** (Task 1 0.912 / accuracy 0.90, Task 2 0.905 / 0.89; displayed entry) | `1ee9da4e…8442` |

Earlier uploads (files in Git history, not copied here): commit `6b76821` → 83.56; commit `0a1e0ba` → 84.62.

**Platform record (read 2026-10-13):** the Final Test Phase lists **12** submissions (4 on 30 Sept, 5 on 9 Oct, 2 on 10 Oct,
1 on 12 Oct; limits 5 a day, 50 a month, 100 in total); this table and `uploads.csv` hold 8. The 4 extra are not yet
identified (probably repeated uploads). Two are ticked "Show on leaderboard": upload 7 (87.24) and upload 8 (86.36); the
board shows the better, 87.24. By our rule the ranked entry is upload 8.

**Update (read 2026-10-16, [`raw/leaderboard-final-test-2026-10-16.json`](raw/leaderboard-final-test-2026-10-16.json)):** a 13th
submission (16 Oct, 23:11 UTC) scored exactly the 88.11 file's numbers (Task 1 0.8571 / accuracy 0.9136, Task 2 0.9051 / 0.8889,
total 88.10775) and is now the displayed entry; recorded as upload 9 in `uploads.csv`. It repeats upload 6's predictions, so it
does not meet the upload rule (at least 3 changes); whether it replaces upload 8 as the ranked entry is Sid's and Charles's call.

## Detective candidates (2026-10-14, user request; not production, not uploaded)

Sid asked for the five files a leader would build to hit the top score, with rule v2 and the upload rule set aside. They are
rebuilt from the leaders' method notes by [`src/build_detective_candidates.py`](../src/build_detective_candidates.py); per-flow
moves are in [`detective-summary.json`](detective-summary.json).

**The clue:** the two tasks score the **same 81 flows with the same labels**: same test ids, identical train+validation labels
per flow, identical fold scores for one prediction set (104). Our Task 2 file scored **0.905** on those flows; our best Task 1
file only 0.857, and the two disagree on just 6 flows. Task 1 may read the Task 2 files (allowed since 022). Training shares
give expected test counts of x 18, mozilla 10, instagram 5, facebook 3; our 0.905 file predicts **24 x** and 7 mozilla, so at
least 6 of its x calls are wrong. Every leader with a Task 2 above 0.905 says they used count assignment.

| # | Folder | Task 1 | Task 2 | Flows changed vs the 0.905 file (T1 / T2) | Mean CV (Task 2 file) | Expected total, if the theory holds |
|---|---|---|---|---|---|---|
| 1 | [`detective-1-flowlens-v8-twin/`](detective-1-flowlens-v8-twin/) | Same as Task 2 | Sigmoid-calibrated SoftVote + training-share counts (102 F2S-S) | 6 / 6 | 0.728 | about 94 (FlowLens v8 Task 2: 0.94) |
| 2 | [`detective-2-flowlens-v9-crossview/`](detective-2-flowlens-v9-crossview/) | Opening + full-flow views averaged, counts | As 1 | 6 / 6 | 0.728 | 94-95 (FlowLens v9 Task 1: 0.96) |
| 3 | [`detective-3-flowlens-isotonic-twin/`](detective-3-flowlens-isotonic-twin/) | Same as Task 2 | Isotonic-calibrated SoftVote + counts (102 F2I-S) | 7 / 7 | 0.739 | about 94, if FlowLens used isotonic |
| 4 | [`detective-4-rahmanij-twin/`](detective-4-rahmanij-twin/) | Same as Task 2 | SoftVote on 17 first-5 columns + counts (104 E1S) | 11 / 11 | 0.700 | about 92.5 (RahmaniJ: 0.92 / 0.92) |
| 5 | [`detective-5-mirror-floor/`](detective-5-mirror-floor/) | Our Task 2 predictions | Unchanged (014) | 0 / 0 | 0.759 | **90.51**, near-certain (both tasks 0.905) |

SHA-256 of `submission.zip` (first 16 hex): 1 `622b93ec11c02953`, 2 `0c933617b8d5b0ad`, 3 `0c72b63e58ff07b0`, 4
`4ce5d7389a174365`, 5 `a8fd551fe64cb1a6`. All five pass the official loader (81/81 ids per task, valid labels) and differ
from every earlier upload in at least 5 test predictions.

**Compliance, for whoever decides to upload:**

- Files use only train+validation labels and the released feature files; Task 2 files read only Task 2 files.
- Not used: the published test counts, per-flow conclusions from our own upload history, the SNI-length proxy.
- The ranking of 1-4 above 5 rests on leaderboard evidence (other teams' scores and our 0.905), not on CV. CV says count
  assignment is worse than production on average (102, 104). This is choosing by leaderboard, which our Goodhart rule
  forbids and condition 1 may cover. Any upload needs Sid's and Charles's decision and a line in the technical report.
- Expected totals are hypotheses. A wrong move into facebook or instagram, the rare classes, costs several points.

## Latest (077 FR) vs the 87.77 file

The best-evidence model by cross-validation (077 FR) produces exactly the 87.77 predictions for both tasks (`submission.json`
byte-identical; the zip differs only in file timestamps). Uploading it would reproduce 87.77, so it is not uploaded. The ranked
entry therefore is both the best leaderboard file and the output of the best cross-validated model.

## Candidate 066 vs the 87.77 file

- Task 2 identical. Task 1: 3 predictions differ (`flow_000095` x → youtube, `flow_000884` youtube → google,
  `flow_000906` youtube → google); all three are among the 8 flows that changed between the 84.62 and 87.77 files.
- Official loader check passed on both formats (81/81 test IDs per task, valid labels).
- Status: candidate for a documented exception ([066](../experiments/066_rest_expert_five_seeds.md)); it was uploaded before
  being adopted, so production did not change. **Ranked entry: the 87.77 file (production), by rule, not by score.**
- Its result (about 86) is information only: 3 differing flows are within 81-flow noise; it is never used to infer
  labels of these flows, to choose files or to steer later experiments.

**Update (2026-10-21):** upload 10, the count-guided candidate 127 (3 Task 1 changes vs uploads 7 and 8, 5 vs upload 9), scored
**90.85** (leaderboard row, [`raw/leaderboard-final-test-2026-10-21.txt`](raw/leaderboard-final-test-2026-10-21.txt): Task 1 45.60
points, macro F1 0.912, accuracy 0.90; Task 2 45.25 points, 0.905, 0.89); it is now the displayed entry. It was uploaded although its rule failed
cross-validation (099 D: flips right 27%, Δ −0.0169) and therefore the upload rule. The score is information about the test set, not
evidence that the rule works; see [127](../experiments/127_count_guided_candidate.md). The submission ID was not recorded.

