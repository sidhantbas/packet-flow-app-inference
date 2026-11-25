---
title: "115: Is facebook vs instagram identifiable from per-flow statistics, and how much of the leaderboard could be benchmark artefacts? (measurement only)"
created: 2026-10-19
creator: sidhantbas
description: "Frozen measurement on the raw released rows: Bayes-error bounds and mutual information for facebook vs instagram, a learning-curve extrapolation, an artefact decomposition (adversarial validation, exact-twin reachability, capture adjacency) and a surrogate-tree shortcut audit of production; checked against Charles's afe-002 and the literature."
source:
  - 048_facebook_diagnostics.md
  - 036_twin_aware.md
  - 039_capture_order.md
  - 107_temporal_label_neighbours.md
  - 114_first_packet_mechanism.md
experiment:
  id: '115'
  tasks: [task1, task2]
  lever: diagnostic
  status: measured
  verdict: 'The app signal is mostly an opening packet-size fingerprint of the capture setup (8 of 12 surrogate-tree splits; top information 1.36 bits); facebook and instagram share Meta''s fingerprint, leaving at least 11-24% irreducible pairwise error (substantially ambiguous on the first 5 packets); test flows have more exact single-label twins than CV (63% vs 54% at equal pool size); session context is strong but off-limits; about 25 facebook flows would be needed for F1 0.8'
---

# 115: Identifiability of facebook vs instagram, and benchmark artefacts

**Status: done 2026-10-19. Protocol frozen (`5dbdfb2`) before any code or run.**
**Verdict: the deeper showstopper is a fingerprint collision. The benchmark is solved mostly by opening packet sizes (a
fingerprint of the capture devices' network stacks); facebook and instagram share Meta's stack, so their fingerprints collide, and
what separates them lives in the whole flow and in session context.** Results are below the protocol.
Do not edit the frozen sections after execution starts. Sid, 2026-10-19: treat the facebook/instagram gap as a research question
(irreducible error, artefact decomposition, one compliant direction), "go ahead and run it". **Measurement only:** no model
change, no test labels, no submission.

## Question

1. **Identifiability:** how much facebook/instagram error is irreducible given the per-flow statistics, whatever the model?
2. **Artefacts:** how much of what top methods exploit could be benchmark artefacts (near-duplicates, capture adjacency, opening
   fingerprints) rather than app behaviour?
3. **Direction:** which single compliant research direction follows?

## Frozen design

**Raw material:** the released rows of both tasks (330 labelled flows; 81 test flows' features, unlabelled); flow order and
`start_rel` for measurement only (never as a model input); the production champion runs' per-flow out-of-fold predictions
(`results/champions.json`); 048's learning curve and Charles's afe-002 numbers (FINDINGS.md).

| # | Measurement | Method |
|---|---|---|
| B1 | Bayes-error bounds, facebook vs instagram (30 Meta flows) and all 6 apps (330 flows) | Leave-one-out 1-NN error $R_1$ on log1p-standardised columns (Task 1: 34; Task 2: 12); Cover–Hart: $\tfrac{M-1}{M}\left(1-\sqrt{1-\tfrac{M}{M-1}R_1}\right) \le R^* \le R_1$ (asymptotic); also LOO 3-NN and 5-NN error |
| B2 | Information per column about facebook vs instagram, and about the app | `sklearn.feature_selection.mutual_info_classif` (nearest-neighbour estimator, 3 neighbours, `random_state` 0), in bits |
| B3 | Facebook flows needed | Fit $F1(n) = a - b\,n^{-c}$ ($a \le 1$) to 048's production curve (2.0, 3.8, 5.4, 7.0, 8.8 training facebook flows → 0.174, 0.398, 0.513, 0.575, 0.674); solve for F1 0.8 and 0.9; afe-002 (2, 4, 6 → 0.036, 0.181, 0.367) shown for comparison only (3 points, 3 parameters) |
| A1 | Train-vs-test shift | Adversarial validation: random forest separating the 330 labelled from the 81 test rows, 5-fold stratified CV AUC, per task |
| A2 | Exact-twin reachability | Share of flows whose exact Task 2 opening (12 columns) occurs in the labelled pool with a single label: test flows vs all 330 labelled; held-out flows vs their training fold (repeated 5-fold, cv_seed 2026); also among flows production calls facebook or instagram |
| A3 | Capture adjacency | For each labelled flow, does the labelled flow closest in `start_rel` share its app? Overall, facebook, instagram; vs the class-frequency baseline |
| A4 | Shortcut audit (Trustee's technique) | Depth-4 decision tree fitted to production's out-of-fold predictions (majority over 10 repeats) on the production columns; fidelity, split columns, and whether each split column is a whole-flow behaviour column or an opening column; Task 1 and Task 2 |
| E | Outside checks | Charles's afe-002 learning curve; literature search on facebook/instagram separability and shortcut learning in encrypted-traffic classification |

**Reading, fixed now:**

- **Identifiability:** facebook vs instagram is "largely identifiable" in a view if the B1 upper bound ($R_1$) is ≤ 0.15, "substantially
  ambiguous" if the B1 lower bound is ≥ 0.15, otherwise "partly ambiguous".
- **Artefacts favour lookup on test** if A2's test share exceeds the CV share by ≥ 5 points or A1's AUC ≥ 0.60.
- **Direction:** the compliant lever with the largest measured headroom among: more facebook flows (B3), opening fingerprints
  (B2/A4), lookup/duplicates (A2), session context (A3, off-limits as a signal).

## Boundaries

No test labels; no `metadata.json` counts; Task 2 measurements use only Task 2 files. Capture time and order are measured, never used
as a model input. No identifiers (no SNI, DNS or IP addresses). No packages installed.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-19 | Protocol frozen and committed | before any code change or run |
| 2026-10-19 | Literature search (before the run) | no published facebook-vs-instagram flow-statistics result found; shortcut learning in encrypted-traffic classification is documented (sources below) |
| 2026-10-19 | `src/exp115_identifiability_and_artefacts.py` run | `115_evidence/measurements.json`, 5 s |
| 2026-10-19 | **Post hoc** check (not in the protocol): A2 with equal pool sizes | test flows looked up in random 264-flow labelled pools (200 draws) |

No other deviation from the frozen protocol. Tools: `shap`, `mapie`, `npeet` and Trustee are not installed and were not installed
(the frozen environment); their methods were applied with scikit-learn and scipy (nearest-neighbour mutual information; a
surrogate decision tree, Trustee's technique).

## Results

Evidence: [`115_evidence/measurements.json`](115_evidence/measurements.json).

### Identifiability (B1-B3)

| View (facebook vs instagram, 30 flows) | LOO 1-NN error | Bayes error (asymptotic bounds) | Reading |
|---|---:|---|---|
| Task 1, 17 whole-flow columns | 0.200 | **0.113 - 0.200** | partly ambiguous |
| Task 1, 34 production columns | 0.367 | 0.242 - 0.367 | substantially ambiguous |
| Task 2, 12 opening columns | 0.367 | **0.242 - 0.367** | substantially ambiguous |

For all 6 apps the bounds are 0.121-0.224 (Task 1) and 0.076-0.145 (Task 2). The bounds are asymptotic and metric-dependent; with
30 flows they are indicative. Adding the 17 opening columns to the 17 whole-flow columns *raises* the facebook/instagram 1-NN error
(0.200 → 0.367): for this pair the opening columns are noise.

**Information (B2, bits):** facebook vs instagram, at most 0.39 bits from one column in Task 1 (`packet_count_up`, then
`bytes_down`, `packet_count_down`, `bytes_up`) and 0.29 in Task 2 (`transport`), against 0.95 bits of class entropy. Across all six
apps the most informative columns are all opening sizes: `p5_bytes_up` 1.36 bits, `p5_up_down_byte_ratio` 1.35,
`p5_mean_pkt_size_up` 1.29.

**Learning curve (B3):** fitted to 048's production curve, facebook F1 would need about **25 training facebook flows for 0.8**
and about **85 for 0.9** (now about 9 per fold). Charles's afe-002 curve (train-only protocol, 3 points) rises more slowly
(196 and 1,453): an outside replication with the same shape and an even steeper data need.

### Artefacts (A1-A4)

| Check | Result |
|---|---|
| A1 Train vs test shift (adversarial AUC) | Task 1 **0.517**, Task 2 **0.556**: no shift |
| A2 Test flows with a single-label exact opening twin | **65.4%** (in all 330) vs **53.8%** for CV held-out flows; **63.2%** in random 264-flow pools (post hoc, 5th-95th 59.3-65.4%). Lookup is right 96.1% of the time when a twin exists. Among production's Meta calls: test 2 of 6, CV 44% |
| A3 Label of the flow captured closest in time | Same app **63.6%** (chance 25.4%); facebook 18.2% (chance 3.3%, ×5.5); instagram **52.6%** (chance 5.8%, ×9.1) |
| A4 Surrogate tree of production (depth 4) | Task 1: CV fidelity 0.742; **8 of 12 splits on opening columns** (`p5_mean_pkt_size_up` ×3, `p5_bytes_up`; youtube vs google split at a first-packet mean of 1379-1387 B). Task 2: fidelity 0.806, all splits on upstream opening sizes |

### Outside checks (E)

- **Charles's afe-002** (independent repository, own protocol): facebook F1 rises with distinct facebook rows (0.036 / 0.181 / 0.367
  at 2 / 4 / 6); reweighting does not replace rows. Same conclusion as B3.
- **Literature:** no published facebook-vs-instagram result from flow statistics was found for MIRAGE (its public release covers
  20 apps; [MIRAGE](https://traffic.comics.unina.it/), [data augmentation study](https://arxiv.org/pdf/2401.10754)). Shortcut learning
  in network-traffic ML is documented: Trustee exposes shortcuts and spurious correlations in published models
  ([Jacobs et al., CCS 2022](https://sites.cs.ucsb.edu/~arpitgupta/pdfs/trustee.pdf)); recent work reports shortcut features in
  encrypted-traffic and app-classification benchmarks ([BiasSeeker, arXiv 2601.10180](https://arxiv.org/abs/2601.10180v1)) and large
  inflation from scenario-specific artefacts ([Politecnico di Torino](https://iris.polito.it/handle/11583/3011672)). These are
  recent and only partly peer-reviewed.

## Verdict

**The deeper showstopper is a fingerprint collision, not scarcity alone.**

1. **The benchmark is solved mostly by a fingerprint.** The most informative columns for all six apps are the upstream sizes of
   the first five packets, and production's decisions follow them (A4). These sizes mark each app's network stack on the capture
   devices (114: they change with the device and app version, which is why our captures did not transfer, 052-063). This is the
   kind of shortcut the literature warns about.
2. **Facebook and instagram share Meta's stack, so their fingerprints collide.** On the first five packets their Bayes error is at
   least about 24% (asymptotic bound); adding opening columns to whole-flow columns makes the pair *harder* to separate. What
   separates them is whole-flow behaviour (volume, packet counts) with at least about 11% irreducible error, and session context.
3. **Session context is strong but off-limits.** An instagram flow's nearest flow in capture time is instagram 9× more often than
   chance (A3). That information is in the benchmark (flows captured in app sessions), not in a single flow, and our rules exclude
   capture time as a signal.
4. **Duplicates favour lookup on test** (63% vs 54% single-label twins at equal pool size, about 9 points). Production already
   memorises exact openings (036, 108); top entries that add lookup or count matching gain from the same artefact.
5. **More data would help, but needs the same capture setup:** about 25 facebook flows for F1 0.8 (B3), which only the organisers'
   setup can produce.

**The one compliant research direction that follows:** *fingerprint-robust app identification.* Measure how much of each model's
accuracy comes from stack fingerprints, by training on the challenge flows and evaluating on our own captures (a different device
and app version: an out-of-distribution test set, Task 1, evaluation only, as captures are allowed for Task 1). Then develop
whole-flow behaviour features whose separation of facebook and instagram survives the device change. It does not move this
leaderboard (the test set shares the capture setup), but it is the honest research contribution for the technical report and
beyond 23 October.
