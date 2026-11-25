# packet-flow-app-inference: findings so far (experiments 001–017)

*ITU AI/ML Challenge "Application Inference from Packet Flows". Summary as of 30 September 2026; submission deadline 23 October 2026. Details for every number are in `experiments/NNN_*.md` and the logged runs in `results/`.*

## Headline

| | Task 1 (full flow) | Task 2 (first 5 packets) |
|---|---|---|
| Baseline RandomForest (CV macro F1) | 0.733 | 0.676 |
| 29 Sept submission (ensemble) | 0.771 | 0.686 |
| **Current submission** | **0.771** | **0.754** |

Two changes moved task 2, both confirmed on three different fold splits:
1. **Drop the timing columns on task 2** (experiment 007): +0.051, every class better.
2. **A Facebook/Instagram second stage on task 2** (experiment 014): +0.018.

On validation, scored with the organisers' own `evaluate()` as a pipeline check: task 1 0.745, task 2 0.778, **total 76.1** (74.1 on 29 Sept).

## The data in one paragraph
There are 411 encrypted flows from one phone recorded over about 44 minutes, labelled with 6 apps (facebook, google, instagram, mozilla, x, youtube): 247 train, 83 validation and 81 test. Task 1 uses statistics of the whole flow; task 2 uses only the first 5 packets. The score is 50 × macro F1 per task. The classes are very unbalanced: Facebook has 11 labelled flows and Instagram 19, and because macro F1 weights every class equally, these two decide much of the score. `server_port` (443 in 409 of 411 flows) and `start_rel` (recording time) are left out.

## How we measure
The validation split has only 83 flows (3 Facebook), so one Facebook flow moves macro F1 by about 7 points. We merge train and validation (330 flows) and use **5-fold cross-validation repeated 10 times** (50 scores), always comparing two models on the same splits. A change counts as better only if it helps on average, wins at least 70% of the splits where it changes anything, and **passes again on two other sets of splits**. Every run is logged locally with its data and code hashes, device, and per-flow predictions, and can be re-verified.

## What we found

**Task 2: timing in the first 5 packets hurts.** Dropping `duration` and the four inter-arrival-time columns improves task 2 by 0.051 (40/50 splits), confirmed with a second model type and on two more split sets. Adding timing back in any form (ratios, rates, burst density) costs about 0.05. Over five packets, timing seems to reflect network delay rather than the app. This matches Charles's permutation result, where shuffling those columns slightly *improved* his task 2 model.

**Task 2: Facebook vs Instagram.** 13 Instagram and 2 Facebook flows share one exact opening pattern. Balanced class weights (needed elsewhere for Facebook) push that pattern to Facebook. A second-stage model trained only on Facebook + Instagram, without class weights, gives it back to Instagram: +0.018, Facebook +0.02–0.04 and Instagram +0.06–0.09, with 52 splits won and 1 lost across three split sets.

**Task 1: timing is what identifies Facebook.** Shuffling the timing columns costs Facebook 0.40 F1 (50-split permutation importance), so timing stays in task 1. Packet size is the strongest group overall; `transport` matters most for Instagram and x.

**Google vs YouTube is near its limit with these features.** A model trained on those two apps alone reaches only 0.82 (task 1) / 0.86 (task 2) balanced accuracy, about what the 6-class model already achieves. Both talk to Google infrastructure the same way, so their flow statistics overlap.

**Mozilla vs x:** timing sharpens the pair's ranking (AUC 0.945 → 0.976 on task 2) but only moves errors from one side to the other.

**Where the task 2 errors are:** 74% of held-out task 2 flows have an exact twin in training and about 94% of those are right; 68% of all errors are on never-seen patterns, mostly google and youtube. Memorising is correct for this data: trees forced to generalise more (larger leaves) lose ~0.02.

**Recording time is not a shortcut:** `start_rel` alone scores 0.51, and adding it lowers the task 2 model.

## What did not help (all measured, none adopted)

| Idea | Task 1 | Task 2 |
|---|---|---|
| Ratio features: relative timing, bytes/s, burst density, downstream share, packet-size variation | −0.007 to +0.004 | timing-based −0.05; others +0.001 |
| CatBoost alone, with categorical `transport`, or as a 4th ensemble member | −0.006 to −0.001 | −0.007 to +0.015 |
| No class weights / square-root weights | −0.014 (Facebook −0.09) | +0.012 (Instagram only; the 014 specialist does it better) |
| Google/YouTube second stage | −0.004 | 0.000 |
| Mozilla/x second stage with timing | — | −0.002 (swaps errors) |
| Larger tree leaves | −0.003 | −0.021 |
| + logistic regression + kNN members (also gated to new patterns) | −0.007 (Facebook −0.075) | +0.006 (just short) |
| Tuned per-class decision weights (004) | −0.003 | −0.039 |

## Current submission
- **Task 1:** average of RandomForest + ExtraTrees + LightGBM (balanced class weights), 17 columns.
- **Task 2:** the same ensemble on 12 columns (no timing), plus a Facebook/Instagram second stage without class weights.
- Trained on train+validation; built by `src/make_submission.py`. Each task reads only its own folder.
- **Expected score from CV:** about 0.771 × 50 + 0.754 × 50 ≈ **76 points**, ±3–4 points per task, mostly from how the 2 test Facebook flows land.
- **Compute:** under 5 s to train per task on a laptop (Apple M4 Pro); a full 50-split evaluation takes about 4 s.

## Compliance
We follow the five official conditions (recorded in `CLAUDE.md`): no test labels or anything derived from them (an earlier sanity check that printed the published test class counts was removed on 30 Sept; it was never used for any decision), no task 1 data in task 2, no identifier recovery, no outside data, and every result reproducible from logged code and data hashes.

## Next steps
1. Round 3, aimed at bigger changes: nested-CV tuning of the ensemble settings, stacking, and a closer look at how the task 2 first-5-packet features are built.
2. Keep choosing models by cross-validation only, not by the leaderboard.
