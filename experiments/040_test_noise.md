---
title: '040: How much of the leaderboard gap is noise? (measurement only)'
created: 2026-10-05
creator: sidhantbas
experiment:
  id: '040'
  tasks:
  - task1
  lever: evaluation
  status: measured
  verdict: '81-flow test noise: the same model scores 0.737-0.917 (5th-95th); our 0.787 sits near the 21st percentile, the leader''s 0.94 near the 98.7th; one facebook flow = 2-4 points'
---
# 040: How much of the leaderboard gap is noise? (measurement only)

- **Date:** 2026-10-05
- **Command:** `.venv/bin/python src/exp040_test_noise.py` (about 20 s)
- **Method:** 20,000 synthetic 81-flow test sets; class mix from the labelled proportions scaled to 81 (stratified split;
  metadata.json not used): google 32, x 18, youtube 13, mozilla 10, instagram 5, facebook 3. Each drawn flow takes one of its 10
  held-out predictions from the production Task 1 run (034). Score = the organisers' macro F1. Repeated with 2 facebook flows.

## 1-2. Spread of Task 1 macro F1 on 81-flow samples

| Mix | Median | 5th pct | 95th pct | Our leaderboard 0.787 | 4th place 0.88 | Leader 0.94 |
|---|---|---|---|---|---|---|
| 3 facebook | 0.834 | 0.737 | 0.917 | 21st percentile | 80th (P >= 0.88: 20%) | 98.7th (P >= 0.94: 1.3%) |
| 2 facebook | 0.829 | 0.709 | 0.921 | 26th percentile | 81st (19%) | 98.2th (1.8%) |

Note: 0.787 was scored by the 022 Task 1 model; these samples use the current production model (034, CV 0.828).

## 3. One or two facebook flows flipping, in an 81-flow sample

| Change | 3 facebook flows | 2 facebook flows |
|---|---|---|
| 1 wrong -> right | +0.046 (+2.3 points) | +0.065 (+3.3 points) |
| 2 wrong -> right | +0.098 (+4.9 points) | +0.156 (+7.8 points) |
| 1 right -> wrong | -0.055 (-2.8 points) | -0.079 (-3.9 points) |
| 2 right -> wrong | -0.119 (-5.9 points) | -0.161 (-8.0 points) |

## 4. Leaderboard structure

The Final Test Phase scores every test flow (`evaluate()` requires all 81 IDs; no subset) and "determines the official ranking".
There is no hidden final set: the visible Final Test Phase score is the final score. The Validation Phase scores public labels.

## Conclusion

Our 0.787 sits in the lower part of our own model's range (about the 21st-26th percentile): partly bad luck on a small test set.
The leader's 0.94 is beyond our 95th percentile (about a 1-2% chance for our model), so most of the gap is a genuinely stronger Task 1
or very favourable sampling, not noise alone. One facebook flow is worth 2-4 points. Caveat: held-out predictions come from models
trained on 264 flows (the final one has 330, and test flows have more near-twins, 036), so the distribution is slightly pessimistic.
