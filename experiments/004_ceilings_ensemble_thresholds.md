---
title: '004: Ceilings, soft-voting ensemble, nested-CV class multipliers, google vs youtube'
created: 2026-09-29
creator: sidhantbas
experiment:
  id: '004'
  tasks:
  - task1
  - task2
  lever: model
  status: adopted
  verdict: 'SoftVote (RF + ExtraTrees + LightGBM): Task 1 0.771 (+0.038, 34/50, adopted by explicit decision in 005); per-class multipliers hurt in all 4 settings; Task 2 identical-vector ceiling 0.930'
  production: SoftVote base learner of every model
---
# 004: Ceilings, soft-voting ensemble, nested-CV class multipliers, google vs youtube

- **Date:** 2026-09-29
- **Scripts:** `src/ceilings.py` (Part A), `src/exp004_ensemble_thresholds.py` (Parts B–D; run with `B`, `C` or `D` as arguments). `separation_report` in `src/exp003_confusion_variants.py` now takes any class pair.
- **CV:** repeated stratified 5-fold × 10 (50 folds) on train+validation (330 flows) per task, `cv_seed=2026`, model seed = fold index. All variants use identical folds.
- **Features:** the 17 default model columns (no `start_rel`, no `server_port`).
- **Verdict rule:** paired Δ > 0 **and** ≥ 35/50 fold wins.

## Part A: Ceilings from identical feature vectors

Rule: every flow in a group with an identical feature vector must get the same prediction. Groups with a single label take that label, and for each mixed group every choice among its labels is tried (exhaustive search).

### Using the 17 model columns (as specified)

| Task | Distinct vectors / flows | Duplicate groups | Mixed groups | Macro F1 ceiling |
|---|---|---|---|---|
| task1_static | 330 / 330 | 0 | 0 | 1.000 |
| task2_realtime_prefix5 | 330 / 330 | 0 | 0 | 1.000 |

**There are no exact duplicates in either task, so this ceiling is trivially 1.0.** The timing columns (`duration`, `mean_iat`, `std_iat`, `min_iat`, `max_iat`) are continuous and differ at the microsecond level even when everything else is identical.

### Extra: size/count columns only (the 17 minus the 5 timing columns, 12 in all)

This shows how much of the problem the *packet sizes and counts* can resolve. From here on, any gain in task 2 has to come from timing.

| Task | Distinct / flows | Duplicate groups | Mixed groups | Macro F1 ceiling | Facebook F1 ceiling | Instagram F1 ceiling |
|---|---|---|---|---|---|---|
| task1_static | 311 / 330 | 10 | 0 | 1.000 | 1.000 | 1.000 |
| task2_realtime_prefix5 | 123 / 330 | 49 | 7 | **0.930** | **0.857** | **0.900** (0.905 if optimised for Instagram alone) |

In task 2, 207 of 330 flows share their size/count vector with at least one other flow, and 80 flows sit in the 7 mixed groups:

| # | Labels mixed | Pattern (transport, pkts up/down, bytes up/down) |
|---|---|---|
| 0 | youtube 24, google 2 | UDP, 2/3, 2762/2666 |
| 1 | x 30, mozilla 5, youtube 2 | TCP, 3/2, 794/140 |
| 2 | youtube 4, google 1 | TCP, 3/2, 796/140 |
| 3 | instagram 2, facebook 1 | UDP, 2/3, 1494/1656 |
| 4 | facebook 1, instagram 1 | UDP, 1/4, 1367/2930 |
| 5 | instagram 4, facebook 1 | UDP, 2/3, 2661/1657 |
| 6 | instagram 1, youtube 1 | TCP, 2/3, 294/222 |

Per-class F1 at the task 2 size/count ceiling: facebook 0.857, google 0.988, instagram 0.900, mozilla 0.935, x 0.954, youtube 0.945. The ceiling is well above the current 0.676, so **the task 2 gap is mostly model error, not a hard limit of the features**.

## Part B: Soft-voting ensemble (mean predict_proba of RF + ExtraTrees + LightGBM, settings from 003)

| Task | Variant | Macro F1 (± fold std) | Paired Δ | W/T/L | facebook | google | instagram | mozilla | x | youtube | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 | RF baseline | 0.7326 ± 0.079 | — | — | 0.486 | 0.811 | 0.691 | 0.847 | 0.876 | 0.685 | — |
| T1 | Soft vote | **0.7705** ± 0.071 | **+0.0379** | 34/0/16 | 0.584 | 0.831 | 0.735 | 0.857 | 0.884 | 0.731 | not better (misses by 1 fold) |
| T2 | RF baseline | 0.6756 ± 0.067 | — | — | 0.361 | 0.823 | 0.563 | 0.780 | 0.845 | 0.682 | — |
| T2 | Soft vote | 0.6856 ± 0.067 | +0.0100 | 29/0/21 | 0.346 | 0.849 | 0.564 | 0.807 | 0.867 | 0.680 | not better |

- On task 1 the ensemble is the strongest thing tried so far: +3.8 points, better on **every** class (Facebook +0.10, youtube +0.05, instagram +0.04). It still falls one fold short of the rule. The paired std of 0.069 is large because Facebook F1 swings with 2–3 flows per fold.
- On task 2 it improves google, mozilla and x slightly, and leaves Facebook, Instagram and youtube unchanged.

## Part C: Per-class probability multipliers, nested CV

- **Method:** multiply the predicted probabilities by one multiplier per class, then take the argmax. The multipliers are chosen from a grid of 17 values between 0.25 and 4 (evenly spaced on a log scale) by coordinate ascent (start at 1, up to 3 passes) to maximise macro F1.
- **Nesting:** inside each outer training fold, a 5-fold stratified inner CV (seed = outer fold index) produces out-of-fold probabilities. The multipliers are fitted on those, the base model is refitted on the whole outer training fold, and the multipliers are applied to the untouched outer fold. The outer fold is never used to choose them.
- **Primary base:** by the verdict rule the ensemble is not confirmed better, so RF is the base. The ensemble has the higher mean in both tasks, so it was also run as a secondary base. Each is compared with itself without multipliers on identical outer folds.

| Task | Variant | Macro F1 (± fold std) | Paired Δ | W/T/L | facebook | google | instagram | mozilla | x | youtube | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 | RF + multipliers | 0.7299 ± 0.078 | −0.0027 | 26/2/22 | 0.444 | 0.817 | 0.708 | 0.829 | 0.879 | 0.702 | not better |
| T1 | Soft vote + multipliers | 0.7491 ± 0.072 | −0.0214 | 11/0/39 | 0.500 | 0.822 | 0.729 | 0.850 | 0.884 | 0.711 | worse |
| T2 | RF + multipliers | 0.6369 ± 0.048 | **−0.0387** | 10/0/40 | **0.175** | 0.824 | 0.565 | 0.751 | 0.838 | 0.669 | worse |
| T2 | Soft vote + multipliers | 0.6639 ± 0.068 | −0.0217 | 14/3/33 | 0.243 | 0.844 | 0.583 | 0.787 | 0.855 | 0.672 | worse |

Learned multipliers, median [min–max] over the 50 outer folds:

| Class | T1 RF | T1 soft vote | T2 RF | T2 soft vote |
|---|---|---|---|---|
| facebook | 1.09 [0.25–3.36] | 1.41 [0.25–4.00] | 0.55 [0.25–4.00] | 1.00 [0.25–4.00] |
| google | 1.68 [0.84–2.38] | 1.00 [0.35–2.83] | 1.30 [0.84–3.36] | 1.00 [0.35–2.83] |
| instagram | 0.59 [0.25–1.00] | 1.00 [0.25–3.36] | 1.00 [0.25–4.00] | 1.00 [0.25–3.36] |
| mozilla | 0.71 [0.35–1.41] | 1.00 [0.25–4.00] | 1.00 [0.25–2.38] | 0.71 [0.25–2.38] |
| x | 1.00 [0.71–1.68] | 1.00 [0.25–2.83] | 1.00 [0.30–2.38] | 1.00 [0.30–4.00] |
| youtube | 1.00 [0.35–2.00] | 1.00 [0.25–4.00] | 1.00 [0.42–2.38] | 1.00 [0.35–4.00] |

**The multipliers overfit.** Nearly every class uses the full grid range across folds. The inner folds contain only 1–2 Facebook flows, so the multiplier that maximises inner macro F1 is essentially random. This hurts Facebook most (task 2 RF: 0.36 → 0.18). `class_weight="balanced"` already rebalances the classes, and at 330 flows there is not enough data to tune decisions on top of it. **Do not use per-class multipliers.**

## Part D: google (n=131) vs youtube (n=55)

### task1_static: top separators (youtube sends larger upstream packets; google receives larger downstream packets)

| Feature | google median [IQR] | youtube median [IQR] | Separation |
|---|---|---|---|
| mean_pkt_size_up | 371 [197–556] | 598 [393–778] | 0.44 |
| up_down_byte_ratio | 0.64 [0.18–1.18] | 1.02 [0.81–1.59] | 0.41 |
| mean_pkt_size_down | 580 [362–948] | 426 [245–563] | 0.33 |
| up_down_packet_ratio | 0.89 [0.64–1.00] | 0.94 [0.84–1.08] | 0.23 |
| bytes_down | 9.0k [6.3k–27k] | 7.6k [5.6k–9.8k] | 0.22 |
| bytes_up | 7.2k [3.7k–10k] | 7.8k [5.6k–30k] | 0.21 |

The timing features (duration and all IAT columns), transport and packet counts do not separate them (≤ 0.07). Separation is "moderate at best": no single feature exceeds 0.44.

### task2_realtime_prefix5: top separators

| Feature | google median [IQR] | youtube median [IQR] | Separation |
|---|---|---|---|
| up_down_byte_ratio | 1.03 [1.02–6.84] | 1.53 [1.04–12.7] | 0.35 |
| bytes_up | 2730 [2659–2758] | 2762 [2680–2972] | 0.26 |
| bytes_down | 2666 [164–2666] | 1374 [140–2666] | 0.22 |
| mean_pkt_size_up | 1363 [985–1374] | 1381 [818–1381] | 0.22 |
| mean_pkt_size_down | 889 [82–889] | 687 [78–889] | 0.19 |

All the timing features have separation ≤ 0.05.

### Identical-vector groups mixing google and youtube

- 17 model columns: **none** in either task.
- Size/count columns only: none in task 1. **Two in task 2:** a UDP 2/3-packet opening of 2762/2666 bytes (youtube 24, google 2), and a TCP 3/2 opening of 796/140 bytes (youtube 4, google 1). Both shared openings are dominated by youtube (24 of 55 youtube flows share the first). Only the timing columns can separate the 3 google flows inside them.

## Conclusions

1. **No confirmed winner in 004.** The RF baseline stays the default in both tasks.
2. **The ensemble is the strongest candidate for task 1** (+0.038, 34/50, better on every class). It is worth re-testing once something reduces the fold noise, or adopting by explicit decision, since it misses the rule by a single fold.
3. **Per-class multipliers are harmful at this data size.** Drop this direction.
4. **The task 2 ceiling from sizes and counts alone is 0.93, and we are at 0.68.** The gap is not a hard limit of the features. Facebook's ceiling is 0.86 (vs 0.36 now). Only 3 Facebook flows are truly indistinguishable from Instagram by size and count.
