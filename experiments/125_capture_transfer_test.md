---
title: "125: Does the facebook/instagram difference learned from our captures transfer to the organisers' flows?"
created: 2026-10-21
creator: sidhantbas
description: "Frozen transfer test: facebook-vs-instagram models trained only on our captured flows (iPhone process-labelled, Android session-labelled), scored on the 30 original labelled Meta flows (train + validation), on three column sets including a label-free within-domain alignment, against the in-domain reference; plus a model-free check of whether each column's facebook/instagram direction agrees across domains."
source:
  - 093_data_limited_analysis.md
  - 121_gates_on_clean_captures.md
  - 123_gates_on_charles_candidates.md
  - 124_low_dose_capture_training.md
experiment:
  id: '125'
  tasks: [task1]
  lever: data
  status: rejected
  verdict: 'No transfer: capture-trained facebook/instagram models score AUC 0.24-0.58 on the 30 original Meta flows (in-domain reference 0.82-0.84); no arm passes (best iPhone SIZE 0.579, p 0.26); the contrast itself is reversed: in the originals facebook flows are smaller than instagram flows in every count and byte column, on our iPhone captures they are larger (direction agrees on 4 of 17 columns in both domains); no fitting method can carry the captures over; capture use closed'
---

# 125: Capture transfer test (facebook vs instagram)

**Status: done 2026-10-21. Protocol frozen (`3599865`) before any code or run.**
**Verdict: the facebook/instagram contrast does not transfer; on our phone it points the other way.** Results are below the
protocol. Do not edit the frozen sections after execution starts.
**User decision (Sid, 2026-10-21, "run A and also build up a motivation of making the data fit in"):** a training use of the
captures for measurement only, as in 124; it changes no rule. Task 1 only, no test data, no model change.

## Motivation: why it is worth trying to make the captures fit

1. **Task 1's facebook problem is a data problem, not a model problem.** The full flow does separate facebook from instagram
   (in-domain AUC about 0.80-0.83, notebook 05), but with 11 facebook flows the boundary is learned from very few points: the
   learning curve was still rising at 100% of the data (+3.6 points from 80% to 100%, 093), and every model-side lever is used up
   (112, 116, 119). The textbook cure for a rare class whose signal exists is **more examples of that class**.
2. **The captures hold 4-5 times more Meta flows than the challenge** (49-52 facebook and 157-174 instagram process-labelled
   iPhone flows, plus 55 / 45 Android ones, against 11 / 19), with labels confirmed twice (120, 122: 100% agreement with Charles).
3. **The failures so far measure the wrong thing for this purpose.** The gates (121, 123) and the training tests (056-058, 063,
   124) ask whether captured flows *look like* challenge flows of the same app in absolute values. They do not: our phones' packet
   sizes and timing differ (device and app versions). But a classifier only needs the **difference between facebook and
   instagram** to point the same way in both domains. In domain-adaptation terms the marginal distribution can shift (covariate
   shift) while the class contrast stays shared. If facebook flows are smaller, shorter and less media-heavy than instagram flows on
   our phone as on the organisers', that contrast is transferable knowledge even though no single captured flow resembles an
   original one.
4. **If the contrast transfers, there is a legitimate way to fit the captures in** that never asks them to look like original
   flows: a capture-trained facebook/instagram expert inside Task 1's Meta decision, or columns aligned within each domain. That is
   the only route left that could add information to the one class that costs us most (about 1 point per Task 1 error, 119).
5. **If it does not transfer, we know why no fitting method can work**, and the report can say so with evidence instead of
   "it failed five times".

**Why it may still fail:** the captured Meta flows sit next to challenge google flows (123), and their composition differs (our
captured instagram flows last a median 24 s against 234 s in training, Charles's audit), so even the contrast may differ.

## Frozen design

**Training data (captures only, never original flows):**

| Domain | Rows | Labels |
|---|---|---|
| iPhone | Charles's candidates at `d3189ba`, profile `observed`: 49 facebook, 157 instagram | process-supported, agree with ours (122) |
| Android | our clean extraction (120), `keep = True`: facebook 55, instagram 45 | session labels, uncertain |

**Test data:** the 30 original labelled Meta flows of train + validation (11 facebook, 19 instagram), Task 1 file.

**Column sets** (from the 17 Task 1 statistics, `basic_features`, `transport` as 0/1):
**ALL** = all 17; **SIZE** = the 11 without the six timing columns (`duration`, `mean_iat`, `std_iat`, `min_iat`, `max_iat`,
`burst_count`); **RANK** = all 17, each column replaced by its percentile within its own domain's Meta rows (captured rows ranked
among the training domain's facebook + instagram rows, original rows among the 30 original Meta rows; no labels used), a
label-free within-domain alignment.

**Arms:** {iPhone, Android} × {ALL, SIZE, RANK} = 6 arms. Model: `SoftVote(seed=0)` (balanced, production settings), fitted on the
captured rows, `predict_proba` facebook on the 30 original flows.

**Metric:** AUC of P(facebook) on the 30 original Meta flows; 95% bootstrap interval (2000 resamples of the 30 flows, seed 0);
one-sided permutation p-value (2000 label shuffles of the 30 flows, seed 0).

**Reference (in-domain):** the same model and column set trained on original Meta flows only, scored out of fold: repeated
stratified 5-fold × 10 on the 30 flows (seed 2026), mean AUC.

**Model-free direction check:** for each of the 17 columns, the sign of median(facebook) − median(instagram) in the originals
and in each capture domain; count the columns whose sign agrees (zero differences count as disagreement).

## Decision rule

- **Transfers:** an arm with AUC ≥ 0.65 and permutation p < 0.05 / 6 (Bonferroni over the 6 arms). Then a follow-up (the
  capture-trained expert inside Task 1's Meta decision, or the RANK alignment) may be frozen as its own experiment on never-used
  seeds, with the user's decision; rule v2 and the upload rule apply before anything reaches production or the leaderboard.
- **Does not transfer:** no arm qualifies. The captures carry no usable facebook/instagram contrast for this data; capture use is
  closed with that reason.

## Boundaries

Train + validation of the original data only (30 Meta flows as test); no test data; no production or submission change; Task 2
untouched.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-21 | Protocol frozen and committed (`3599865`) | before any code change or run |
| 2026-10-21 | Runner committed and run (65 s) | [`125_evidence/transfer.json`](125_evidence/transfer.json) |

No deviation from the frozen protocol.

## Results

Test: the 30 original Meta flows (11 facebook, 19 instagram). Training: iPhone 49 facebook / 157 instagram; Android 55 / 45.

| Arm | Transfer AUC | 95% bootstrap | Permutation p | In-domain reference | Transfers? |
|---|---:|---|---:|---:|---|
| iPhone / ALL | 0.569 | 0.32-0.79 | 0.28 | 0.843 | ❌ |
| iPhone / SIZE | 0.579 | 0.34-0.81 | 0.26 | 0.820 | ❌ |
| iPhone / RANK | 0.512 | 0.29-0.73 | 0.48 | 0.838 | ❌ |
| Android / ALL | 0.411 | 0.20-0.64 | 0.77 | 0.843 | ❌ |
| Android / SIZE | 0.402 | 0.20-0.62 | 0.81 | 0.820 | ❌ |
| Android / RANK | 0.239 | 0.07-0.43 | 0.99 | 0.838 | ❌ |

**Direction check** (sign of median facebook − median instagram per column): the originals and the captures agree on **4 of 17**
columns in both domains, fewer than chance. The core contrast is reversed:

| Columns | Originals | iPhone captures | Android captures |
|---|---|---|---|
| packet counts, bytes, mean packet sizes (6 columns) | facebook **smaller** | facebook **larger** (6 of 6) | larger (4 of 6) |
| gaps (mean, std, max) and up/down packet ratio | facebook larger | facebook smaller | facebook smaller |
| duration | facebook shorter | shorter | shorter |

## Verdict

**No arm transfers; capture use is closed, now with the reason.**

1. **The facebook/instagram difference on our phone is the opposite of the organisers'.** In their data facebook flows are the
   small ones and instagram flows carry the media (notebook 05: no facebook flow above about 100 kB downstream). On our phone the
   captured instagram sessions produce many short flows (median 24 s, Charles's audit) while facebook flows are larger. A model
   trained on our contrast learns "facebook = bigger", which is wrong on the challenge data: that is why every capture-training
   test lowered facebook (056, 124).
2. **The motivation's key assumption fails:** the class contrast is not shared across domains, so it is not only a covariate
   shift that alignment could fix. The label-free RANK alignment does not help (iPhone 0.512), as expected when the contrast itself
   differs.
3. **The Android RANK arm's 0.239 is a reversed signal,** not a usable one: flipping it would be a post-hoc choice on 30 flows, and
   its labels are session-only. It is recorded, not used.
4. **For the report:** our captures came from a different phone, app versions and usage pattern, and the facebook-vs-instagram
   difference itself differs between that population and the challenge data; no weighting, filtering or alignment can transfer it.
