---
title: '003: Confusion diagnosis and small model/feature variants'
created: 2026-09-29
creator: sidhantbas
experiment:
  id: '003'
  tasks:
  - task1
  - task2
  lever: model
  status: rejected
  verdict: 'balanced_subsample, log1p, ExtraTrees or LightGBM alone, facebook/instagram duplication: all within noise; RF stays the default'
---
# 003: Confusion diagnosis and small model/feature variants

- **Date:** 2026-09-29
- **Script:** `src/exp003_confusion_variants.py`. It uses `src/cv.py`, which now also accepts a `resample` hook applied to the training fold only and returns pooled out-of-fold predictions.
- **CV:** repeated stratified 5-fold × 10 (50 folds) on train+validation (330 flows) per task, `cv_seed=2026`, model seed = fold index. All variants use identical folds.
- **Baseline features:** the 17 default features (no `start_rel`, no `server_port`).
- **Decision rule, set in advance:** a variant counts as better only if the paired mean Δ is > 0 **and** it wins ≥ 35/50 folds.

## Part A: Confusion (baseline RF, pooled over 50 folds; each flow is predicted 10 times)

### task1_static (rows = true, columns = predicted)

| | facebook | google | instagram | mozilla | x | youtube |
|---|---|---|---|---|---|---|
| **facebook** (110) | **50** | 23 | 18 | 0 | 10 | 9 |
| **google** (1310) | 10 | **990** | 25 | 52 | 64 | 169 |
| **instagram** (190) | 24 | 10 | **136** | 4 | 1 | 15 |
| **mozilla** (410) | 0 | 6 | 0 | **394** | 10 | 0 |
| **x** (730) | 0 | 3 | 4 | 61 | **651** | 11 |
| **youtube** (540) | 1 | 97 | 23 | 15 | 19 | **395** |

- **Facebook** (recall 0.45, precision 0.59): true Facebook flows are predicted as google 23, instagram 18, x 10 and youtube 9. Flows predicted as Facebook are really instagram 24 and google 10.
- **Instagram** (recall 0.72, precision 0.66): true Instagram flows are predicted as facebook 24, youtube 15 and google 10. Flows predicted as Instagram are really google 25, youtube 23 and facebook 18.
- Largest confusions by volume: **google ↔ youtube** (169 + 97) and **x ↔ mozilla** (61 + 52).

### task2_realtime_prefix5

| | facebook | google | instagram | mozilla | x | youtube |
|---|---|---|---|---|---|---|
| **facebook** (110) | **46** | 0 | 50 | 0 | 14 | 0 |
| **google** (1310) | 3 | **1016** | 0 | 57 | 57 | 177 |
| **instagram** (190) | 62 | 0 | **108** | 0 | 10 | 10 |
| **mozilla** (410) | 0 | 22 | 0 | **335** | 52 | 1 |
| **x** (730) | 0 | 11 | 3 | 50 | **657** | 9 |
| **youtube** (540) | 0 | 107 | 14 | 7 | 35 | **387** |

- **Facebook** (recall 0.42, precision 0.41): true Facebook flows are predicted as instagram 50 and x 14. Flows predicted as Facebook are really instagram 62 and google 3.
- **Instagram** (recall 0.57, precision 0.62): true Instagram flows are predicted as facebook 62, x 10 and youtube 10. Flows predicted as Instagram are really facebook 50 and youtube 14.
- In task 2 the Facebook/Instagram confusion is almost entirely **between the two of them**; they are rarely confused with the other four apps. Google ↔ youtube (177 + 107) is again the largest confusion by volume.

## Part A: Facebook (n=11) vs Instagram (n=19) feature distributions (train+validation labels only)

"Separation" is |2·AUC − 1|: 0 means the distributions overlap completely, 1 means they are perfectly separated. The full tables are in the script output.

### task1_static: top separators (Facebook flows are small and slow; Instagram flows are bulk transfers)

| Feature | facebook median [IQR] | instagram median [IQR] | Separation |
|---|---|---|---|
| bytes_down | 5.1k [3.4k–12k] | 54k [17k–2.5M] | 0.70 |
| packet_count_down | 20 [12–48] | 329 [50–2757] | 0.68 |
| bytes_up | 7.4k [2.2k–16k] | 280k [13k–627k] | 0.66 |
| burst_count | 6 [5–10] | 35 [10–57] | 0.64 |
| packet_count_up | 25 [12–42] | 547 [42–1416] | 0.61 |
| mean_iat | 5.8 s [0.29–7.5] | 0.38 s [0.05–1.2] | 0.44 |
| std_iat | 17.6 [1.6–18.8] | 2.3 [0.78–4.3] | 0.38 |

Weakest: std_pkt_size_down/up, min_iat and max_iat (≤ 0.11).

### task2_realtime_prefix5: little separation; Instagram has a fixed opening pattern

| Feature | facebook median [IQR] | instagram median [IQR] | Separation |
|---|---|---|---|
| std_pkt_size_down | 219 [8–500] | 513.6 [513.4–513.6] | 0.48 |
| bytes_up | 1365 [661–1550] | 1509 [1430–2661] | 0.45 |
| min_iat | 0 [0–0.001] | 0 [0–0] | 0.31 |
| transport (udp=1) | 1 [0–1] | 1 [1–1] | 0.31 |
| mean_pkt_size_up | 803 [220–1348] | 1294 [751–1330] | 0.19 |

All other features have separation ≤ 0.17. Counts, burst_count and bytes_down are essentially identical between the two.

**Key finding:** 15 train+validation flows share one exact first-5-packet pattern: 2 upstream + 3 downstream packets, bytes_down ≈ 1656, std_pkt_size_down ≈ 513.5, UDP. **Every one of them is Instagram (13) or Facebook (2).** No google, mozilla, x or youtube flow has it. This signature marks the two apps as a group, but a Facebook flow with it cannot be told apart from an Instagram one using these features. Facebook's wider IQRs show that its other 9 flows are more varied.

## Part B: Variants vs baseline (paired, identical folds)

### task1_static

| Variant | Macro F1 (± fold std) | Paired Δ | Wins / ties / losses | Facebook F1 | Instagram F1 | Verdict |
|---|---|---|---|---|---|---|
| a. RF balanced (baseline) | 0.7326 ± 0.079 | — | — | 0.486 | 0.691 | — |
| b. RF balanced_subsample | 0.7369 ± 0.090 | +0.0043 | 33 / 0 / 17 | 0.434 | 0.727 | not better |
| c. log1p + bytes_per_packet | 0.7307 ± 0.081 | −0.0019 | 22 / 9 / 19 | 0.480 | 0.689 | not better |
| d. ExtraTrees balanced | 0.7476 ± 0.079 | +0.0150 | 34 / 0 / 16 | 0.418 | 0.691 | not better (just misses) |
| e. LightGBM small | 0.7555 ± 0.072 | +0.0229 | 26 / 0 / 24 | 0.556 | 0.728 | not better |
| f. RF + oversample fb/ig | 0.7334 ± 0.076 | +0.0008 | 30 / 3 / 17 | 0.465 | 0.701 | not better |

### task2_realtime_prefix5

| Variant | Macro F1 (± fold std) | Paired Δ | Wins / ties / losses | Facebook F1 | Instagram F1 | Verdict |
|---|---|---|---|---|---|---|
| a. RF balanced (baseline) | 0.6756 ± 0.067 | — | — | 0.361 | 0.563 | — |
| b. RF balanced_subsample | 0.6655 ± 0.064 | −0.0101 | 20 / 0 / 30 | 0.241 | 0.623 | not better |
| c. log1p + bytes_per_packet | 0.6824 ± 0.062 | +0.0068 | 29 / 8 / 13 | 0.351 | 0.566 | not better |
| d. ExtraTrees balanced | 0.6851 ± 0.057 | +0.0095 | 30 / 0 / 20 | 0.296 | 0.573 | not better |
| e. LightGBM small | 0.6770 ± 0.073 | +0.0013 | 25 / 0 / 25 | 0.323 | 0.574 | not better |
| f. RF + oversample fb/ig | 0.6743 ± 0.071 | −0.0013 | 24 / 5 / 21 | 0.324 | 0.568 | not better |

**No confirmed winner in either task.** The baseline RF stays the default.

## Notes on each variant

- **c is close to a no-op by construction.** `bytes_up / packet_count_up` equals `mean_pkt_size_up` in the data (max difference 5e-10), and the same holds downstream. log1p is monotonic, so it does not change which splits a tree can make. The only real change is two duplicate columns, which alter the random feature sampling. The ties (9 and 8 folds) and small Δ match that.
- **f adds almost nothing on top of `class_weight="balanced"`.** Oversampling details: Facebook and Instagram rows are duplicated at random, within the training fold only, up to that fold's mozilla count. Because the class weights are recomputed after resampling, each class's total weight stays the same. The only change is that bootstrap samples see more copies of the rare rows.
- **d (ExtraTrees) on task 1** is the nearest miss: +1.5 points, 34/50 wins, and better scores on google, mozilla and x. It is *worse* on Facebook (0.42 vs 0.49) in both tasks.
- **e (LightGBM) on task 1** has the largest mean gain (+2.3) and the best Facebook score (0.56), but it wins only 26/50 folds, so the gain comes from a few big folds. The two models behave differently, which could make them useful in an ensemble later.
- **b** trades Facebook for Instagram in both tasks. On task 2 it cuts Facebook from 0.36 to 0.24.

## Ideas for next experiments

1. **Task 2, Facebook/Instagram:** the task 2 features show a limit for this pair. Flows with the shared opening pattern cannot be told apart from these features alone. Gains will more likely come from the other 9 Facebook flows and from the non-signature Instagram flows.
2. **Task 1, Facebook:** use volume and timing (bytes, packet counts, mean_iat) together; Facebook flows are small, slow and bursty. Possibly add a two-stage "Meta group, then which app" classifier.
3. **Google ↔ youtube** is the largest confusion by volume (about 270 of 3300 predictions in each task). YouTube F1 of about 0.68 costs as much macro F1 as Instagram does.
4. **Test a RF + ExtraTrees + LightGBM probability average** against the baseline on paired folds.
