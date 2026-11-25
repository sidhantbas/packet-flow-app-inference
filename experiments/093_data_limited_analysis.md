---
title: "093: Data-limited analysis (user brief, 5 x 5 CV)"
created: 2026-10-10
creator: sidhantbas
description: Pointer to the data-limited residual-error analysis in data_limited_analysis/ (protocol, scripts, outputs and report).
relation:
  - ../data_limited_analysis/PROTOCOL.md
  - ../data_limited_analysis/REPORT.md
experiment:
  id: 093
  tasks:
  - task1
  - task2
  lever: diagnostic
  status: measured
  verdict: 'Data-limited analysis: learning curve still rising (+3.6 points from 80% to 100%), label noise about 0; derivable features, self-training and constraints all tie'
---

# 093: Data-limited analysis

**Status: done 2026-10-10.** Protocol: [data_limited_analysis/PROTOCOL.md](../data_limited_analysis/PROTOCOL.md) (committed in
`e0748ee` before Phases 1-5). Report: [data_limited_analysis/REPORT.md](../data_limited_analysis/REPORT.md).

**Verdict:** data-limited. CV baseline 80.90 ± 4.74 (production, 5 × 5); 88.11 is a leaderboard score and not reproducible by CV.
Learning curve still rising (+3.6 points from 80% to 100% of training rows; train–validation gap 15.7). Label-noise cost about 0
(removing suspects ties or hurts). Five derivable feature hypotheses, self-training and monotonic constraints all tie. Confusable
pairs share openings and differ in body behaviour (Task 2: half are exact duplicates). Next actions: more labelled flows from
the challenge's own setup, richer per-flow data, and identifying the capture-setup difference. Runs use a 5 × 5 CV outside
`runlog` (different fold scheme), with every seed logged in the phase JSON files.
