---
title: "089: The near-miss bundle, judged on five never-used split sets"
created: 2026-10-10
creator: sidhantbas
description: Frozen protocol and results for combining the near-miss ideas that were positive across their five seeds (rest-of-flow expert, instagram-protecting doorman, scoped H1 on top of production; Task 2 mozilla verifier) and judging the bundle on cv_seeds 2031-2035, which no earlier experiment used.
source:
  - 066_rest_expert_five_seeds.md
  - 087_doorman_protects_instagram.md
  - 036_twin_aware.md
  - 085_pair_verifier_sweep.md
  - 075_rest_expert_plus_nonmeta_thresholds.md
experiment:
  id: 089
  tasks:
  - task1
  lever: model
  status: adopted
  verdict: 'Near-miss bundle (rest-of-flow expert + facebook-only rescue + scoped exact-opening override): BETTER on 5 never-used seeds (mean +0.0141); Task 2 bundle fails'
  production: Task 1 production since 10 Oct (models.task1_bundle)
---

# 089: The near-miss bundle on five never-used split sets

**Status: done 2026-10-10. Protocol frozen (`21e1c51`) before any code change or run.**
**Verdict: B1 (Task 1 bundle) BETTER on all five fresh seeds, mean +0.0141; test file differs from 88.11 in two flows. B2 (Task 2) fails (2 of 5, 51 wins / 0 losses).** Results are below.
Do not edit the frozen sections after execution starts. User 2026-10-10: macro view, "okay run it". Several ideas were positive
on most or all seeds but each below the rule's detection limit (about +0.010). Combined, gains on different classes may add up.
Because the members were picked after many results, the bundle is judged only on **cv_seeds 2031-2035**, never used before
(checked in `results/index.jsonl`), which act as a fresh referee for the whole selection.

## Membership (rule fixed now; evidence already logged)

Rule: a near-miss joins if its mean Δ against production over its five seeds was > 0, it uses only allowed inputs, and no logged
experiment showed it adds nothing on top of another member; of two members sharing a component, the larger mean Δ stays.

| Idea | Mean Δ (5 seeds) | Decision |
|---|---:|---|
| 065/066 R: rest-of-flow expert (third expert in the Meta gate's average) | +0.0066 | ✅ in |
| 087 IG: Meta gate rescues into facebook only | +0.0020 | ✅ in |
| 036 scoped H1: exact-opening override outside facebook/instagram | +0.003 to +0.006 (passed rule v2 on 6 sets) | ✅ in |
| 085 T2-MG: Task 2 google-vs-mozilla verifier for mozilla calls | +0.0027 | ✅ in (Task 2) |
| 062 non-Meta F/2 thresholds | +0.0030 | ❌ 075: adds nothing on top of R |
| 077 FR: fingerprint + rest experts | +0.0062 | ❌ shares R with 066, smaller mean; fingerprint alone WORSE ×5 |
| 078 TabPFN expert | +0.0027 | ❌ pretrained outside model (team rule) |

## Frozen arms

- **B1 (Task 1):** production 084 ALL with its 034 base replaced by 065's `RestExpertMetaGate(arm="R")` plus 087's rule (a flow
  the gate calls instagram while the two-clerks model calls it non-Meta keeps the two-clerks label); then the two 084 verifiers
  (trained and applied on the 34 production columns, as in 084); then 036's scoped H1 override. Features
  `cv.task1_prefix_rest_features` (34 production + 11 rest-of-flow columns, derived from the released files of both tasks).
- **B2 (Task 2):** production `task2_model` + 085's T2-MG verifier (`exp085_task2_verifier.MozillaVerifier`).

The exam result of 066's file (about 86, three changed flows) is known; it plays no part in membership or decisions.

## Decision rule

- Production references are run first on cv_seeds 2031-2035 (Task 1 `task1_pair_verifiers`, Task 2 `task2_model`).
- Each arm vs its production reference on each of the five seeds through `runlog`. **Pass: rule v2 BETTER on all five.** No
  other seed is used for the decision.
- B1 pass: build the test file (test features only), official loader, count differences from the 88.11 file. A differing file
  is the candidate for the last submission, chosen on this CV evidence before any score (user approval). B2 pass: Task 2
  candidate (its test predictions are already known to equal production's, 085).

## Boundaries

Train+validation only for model choice; test features only to build files; Task 2 reads only Task 2 files; nothing pretrained;
no captures; no capture time or order. Production changes need the user's approval.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-10 | Protocol frozen and committed | before any code change or run; cv_seeds 2031-2035 unused (0 runs in `index.jsonl`) |
| 2026-10-10 | Runner committed (`0942f53`; the front-matter source link to 036 corrected, protocol text unchanged) | |
| 00:29-00:33 | Production references and B1/B2 on cv_seeds 2031-2035 | runs `…_089_T1_production_s203N`, `…_089_B1_s203N`, `…_089_T2_production_s203N`, `…_089_B2_s203N` (N = 1-5) |
| after the runs | B1 test file (test features only), official loader | 2 Task 1 changes vs the 88.11 file; saved as `submissions/production-089-bundle/` |

No deviation from the frozen protocol.

## Results

### B1, Task 1 bundle vs production (084 ALL), fresh seeds

| Seed | Δ macro F1 | W / L / T | Verdict | facebook | google | instagram | mozilla | x | youtube | Flows fixed / broken |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 2031 | +0.0152 | 36 / 11 / 3 | BETTER | +0.003 | +0.015 | +0.014 | +0.024 | +0.013 | +0.023 | 7 / 4 |
| 2032 | +0.0149 | 39 / 6 / 5 | BETTER | −0.004 | +0.014 | +0.027 | +0.019 | +0.007 | +0.027 | 4 / 2 |
| 2033 | +0.0162 | 34 / 14 / 2 | BETTER | +0.009 | +0.015 | +0.007 | +0.017 | +0.005 | +0.045 | 6 / 2 |
| 2034 | +0.0124 | 36 / 10 / 4 | BETTER | −0.004 | +0.009 | +0.017 | +0.021 | +0.008 | +0.024 | 7 / 3 |
| 2035 | +0.0116 | 36 / 12 / 2 | BETTER | 0.000 | +0.011 | +0.016 | +0.017 | +0.006 | +0.020 | 7 / 3 |

Mean Δ **+0.0141** (about the sum of the members' separate means, +0.013); 181 wins, 53 losses (77% of non-tied folds); every
non-Meta class and instagram better on every seed; facebook within ±0.009. Flows fixed on every seed: `flow_000044` (youtube,
was google); on 4 of 5: `flow_000671` (google, was mozilla), `flow_000147` (x, was google).

### B2, Task 2 bundle vs production, fresh seeds

| Seed | Δ | W / L / T | Verdict |
|---|---:|---|---|
| 2031 | +0.0032 | 13 / 0 / 37 | BETTER |
| 2032 | +0.0025 | 9 / 0 / 41 | INCONCLUSIVE (9 non-tied < 10) |
| 2033 | +0.0029 | 11 / 0 / 39 | BETTER |
| 2034 | +0.0019 | 9 / 0 / 41 | INCONCLUSIVE (9 non-tied < 10) |
| 2035 | +0.0025 | 9 / 0 / 41 | INCONCLUSIVE (9 non-tied < 10) |

51 wins, 0 losses, but BETTER on 2 of 5: fails the frozen rule (its test predictions equal production's anyway, 085).

### B1 test file

Differs from the 88.11 file in two Task 1 flows: `flow_000095` google → youtube and `flow_000906` youtube → google. Task 2
unchanged. Official loader: both formats parse, 81/81 IDs per task, valid labels. Saved as `submissions/production-089-bundle/`
(zip SHA-256 `f84d9002…b004`, json `dc76e654…a679`). Both flows were also among the three that 066's file changed; that file's
exam result is known and, by the frozen rule, plays no part in this decision.

## Verdict

**B1 passes: rule v2 BETTER on all five never-used split sets (mean +0.0141).** The near-misses add up because they fix
different classes (rest-of-flow expert: google/youtube; doorman rule: instagram; scoped H1: exact non-Meta openings), and the
gain now clears the referee's detection limit on a referee that never took part in choosing the members. It is the
best-evidence Task 1 model of the project and the candidate for the last submission (user approval; adoption into
`models.TASK_MODELS` also needs it). **B2 fails** (2 of 5).
