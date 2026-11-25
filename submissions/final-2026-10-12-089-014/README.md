---
title: "Final submission candidate (2026-10-12): Task 1 089 + Task 2 014"
created: 2026-10-12
creator: sidhantbas
description: Final candidate built from the production models fitted on all labelled data, with configuration, hashes, validation results, comparison with earlier uploads, verified and unverified platform constraints, and the recommendation.
relation:
  - ../../experiments/098_facebook_audit_and_final_candidate.md
  - ../../experiments/097_reliability_089_vs_084.md
  - ../README.md
---

# Final submission candidate: 089 + 014

**Recommendation: do not upload this file. It is byte-identical to the current ranked entry
([`production-089-bundle/`](../production-089-bundle/), 87.24), so another upload cannot change the score.** Keep the existing
submission and resolve the platform question below if a choice between earlier uploads is possible.

## Files

| File | Content | SHA-256 |
|---|---|---|
| `submission.json` | Both tasks, 81 flows each | `dc76e654…a679` (identical to `production-089-bundle/submission.json`) |
| `submission.zip` | `task1_static.csv`, `task2_realtime_prefix5.csv` | `3bb46530…7dcf` (zip timestamps differ between builds; the JSON is the reproducible artifact) |
| [`config.json`](config.json) | Models, features, inputs, exclusions, command | — |
| [`manifest.json`](manifest.json) | Git commit, code and data SHA-256 | — |
| [`validation.json`](validation.json) | All checks below | — |
| [`comparison.json`](comparison.json) | Prediction differences vs earlier uploads | — |

**Reproduce:** `.venv/bin/python src/make_final_candidate.py` (builds the files twice and checks the JSON is byte-identical;
production artifacts are not touched).

## Models (selected by cross-validation only)

| Task | Model | Inputs | Local evidence |
|---|---|---|---|
| Task 1 | `models.task1_bundle` (089): three experts (whole flow, first five packets, rest of flow), Meta gate with facebook-only rescue, google-vs-instagram and google-vs-x verifiers, exact-opening override | 34 columns: 17 Task 1 + 17 disclosed Task 2 statistics of the same flow; 11 rest-of-flow columns derived inside the model | CV macro F1 0.849 (5 × 10, seed 2026); beats 084 on ordinary and twin-aware folds (+0.014 to +0.017; experiment 097) |
| Task 2 | `models.task2_model` (014): balanced SoftVote + unweighted facebook/instagram stage | 12 no-timing columns, `task2_realtime_prefix5/` only | CV macro F1 0.754 (5 × 10, seed 2026) |

Combined local estimate: 80.90 ± 4.74 points (5 × 5 CV, both tasks). Fitted on train + validation (330 flows), seed 0. These are
local estimates on the same 330 flows used for model selection; they are not a promise about the private test score.

## Validation (all passed)

| Check | Task 1 | Task 2 |
|---|---|---|
| Predictions / test flows | 81 / 81 | 81 / 81 |
| IDs equal test features and sample submission, each once | ✅ | ✅ |
| Missing / extra predictions | 0 / 0 | 0 / 0 |
| Labels within the six allowed | ✅ | ✅ |
| `flow_id`, `split`, `start_rel`, `server_port` absent from model inputs | ✅ | ✅ |
| Files read outside the task folder | Task 2 feature files (allowed for Task 1; disclosed) | **none** |
| Official loader parses JSON and ZIP | ✅ | ✅ |
| Pipeline code reads no `metadata.json` / `label_counts` | ✅ | ✅ |
| Rebuild byte-identical | ✅ | ✅ |

Test labels, test `label_counts`, recovered identifiers, timestamps and capture order are not used anywhere.

## Differences from earlier uploads

| Compared with | Task 1 changed | Task 2 changed | Transitions |
|---|---:|---:|---|
| `production-089-bundle/` (upload 7, ranked entry, 87.24) | **0** | **0** | identical file |
| `best-88.11-production-084/` (upload 6, best score, 88.11) | 2 | 0 | `flow_000095` google → youtube, `flow_000906` youtube → google |

## Platform constraints

| Item | Status | Source |
|---|---|---|
| Format: JSON with `task1_static` and `task2_realtime_prefix5` objects, or ZIP with two CSVs (`flow_id,app`) | ✅ verified | `data/official/templates/submission_guidelines.html` |
| Every required `flow_id` present, no unknown IDs, labels from the six | ✅ verified | `evaluation_details.html` |
| Leaderboard ordered by total score; Final Test Phase decides the official ranking | ✅ verified | `evaluation_details.html` |
| Supporting code and a short technical report may be requested | ✅ verified | `submission_guidelines.html` |
| Deadline | ⚠️ inconsistent: 23 October 2026 (AGENTS.md) vs "challenge end 24 October 2026" (Charles's README timeline); **timezone not documented** | treat 23 October as the safe deadline |
| Upload allowance remaining | ❌ unverified (7 uploads counted locally) | platform page |
| Whether the best, the latest or a chosen upload is ranked | ❌ unverified | platform page |
| Whether earlier uploads remain eligible | ❌ unverified | platform page |

## Recommendation

1. **Retain the existing submission.** This candidate equals the current ranked entry; uploading it again changes nothing.
2. **Resolve one platform question first:** whether the platform ranks the latest upload, the best one, or one the team selects.
   This decides which of the two existing files (87.24 or 88.11) counts. By the project rule fixed before the scores were seen,
   the CV-supported choice is 089 (this file); choosing 084 because its leaderboard score was higher would be selection by test
   score.
