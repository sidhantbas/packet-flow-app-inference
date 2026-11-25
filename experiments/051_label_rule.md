---
title: '051: Which labelling rule did the organisers use? (measurement only)'
created: 2026-10-08
creator: sidhantbas
description: Do facebook flows sit in their own time blocks (labels by app in use) or inside other apps' activity, mainly Instagram's (labels by destination server)?
experiment:
  id: '051'
  tasks:
  - task1
  - task2
  lever: diagnostic
  status: measured
  verdict: 'Labelling rule: no facebook time blocks; facebook starts together with instagram (2.9x); leans toward destination-based labels, not proven'
---
# 051: Which labelling rule did the organisers use? (measurement only)

- **Date:** 2026-10-08
- **Question:** Do facebook flows sit in their own time blocks (labels by app in use) or inside other apps' activity, mainly Instagram's (labels by destination server)?
- **Status:** done
- **Script:** `src/exp051_label_rule.py` (about 1 min)
- **Runs:** none (no model); labelled flows' `start_rel` and labels only
- **Reference:** none; production unchanged

## Hypothesis

From the 046–049 discussion, three ways the organisers could have labelled a flow "facebook":

- **A, app session:** the Facebook app was open when the flow started.
- **B, socket owner:** the Facebook app process opened the connection.
- **C, destination:** the flow went to a Facebook-branded server.

Under C, the Instagram app's background connections to Facebook servers are labelled facebook, which fits the small count
(11), no media, keep-alive-like flows and openings identical to Instagram's (041, 049). Under A and B, facebook flows should
form their own blocks of activity. `start_rel` is used to understand the labels, never as a model input (039).

## Setup

- 330 labelled flows (test flows have no labels, so the timeline has 20% gaps).
- **Fixed before running:** block of a flow = most common label among the other labelled flows starting within ±60 s
  (sensitivity ±30 s and ±120 s), with 1,000 label shuffles over the same start times as the baseline. The decision rule is
  in the script docstring: C needs facebook mostly in Instagram blocks and the app classes in their own blocks; A/B needs
  facebook own-block share ≥ 0.5.
- **Post hoc (designed after seeing the first result):** co-start test, the share of a class's flows with a flow of
  another class starting within ±2 s or ±10 s, against the same shuffles.

## Results

**1. Time blocks (±60 s), as fixed before running:**

| Class | n | Own block | Facebook in block of | Shuffled own (median) | p (own > shuffled) |
|---|---|---|---|---|---|
| facebook | 11 | 0.00 | google 0.73, x 0.18, instagram 0.09 | 0.00 | 1.000 |
| google | 131 | 0.74 | | 0.75 | 0.566 |
| instagram | 19 | 0.00 | | 0.00 | 1.000 |
| mozilla | 41 | 0.02 | | 0.00 | 0.268 |
| x | 73 | **0.90** | | 0.07 | 0.000 |
| youtube | 55 | 0.07 | | 0.02 | 0.172 |

**Verdict under the fixed rule: unclear.** No facebook blocks exist (own share 0.00, so A/B is not supported), but google
dominates almost every window: 58% of Instagram, 53% of YouTube and 49% of Mozilla flows sit in Google-dominated windows. A
small class can never own a block, so the test cannot show Instagram blocks either. Only X has clear sessions of its own.

**2. Post hoc: which classes start together** (share of row-class flows with a column-class flow starting within ±2 s;
enrichment against shuffles; bold = p < 0.05 and enriched):

| Row class | facebook | google | instagram | mozilla | x | youtube |
|---|---|---|---|---|---|---|
| facebook | 0.18 (2.3x, p 0.37) | 0.27 (0.5x) | 0.18 (1.2x, p 0.50) | 0.09 (0.3x) | 0.18 (0.5x) | 0.00 |
| google | 0.02 (0.3x) | 0.50 (1.0x, p 0.67) | 0.01 (0.1x) | 0.11 (0.4x) | 0.08 (0.2x) | 0.08 (0.2x) |
| instagram | **0.26 (2.9x, p 0.038)** | 0.05 (0.1x) | **0.68 (5.1x, p 0.000)** | 0.00 | 0.11 (0.3x) | 0.16 (0.5x) |
| mozilla | 0.10 (1.1x) | 0.24 (0.5x) | 0.00 | **0.78 (3.0x, p 0.000)** | 0.39 (1.0x) | 0.17 (0.5x) |
| x | 0.11 (1.3x) | 0.16 (0.3x) | 0.03 (0.2x) | 0.19 (0.7x) | **0.79 (2.1x, p 0.000)** | 0.19 (0.6x) |
| youtube | 0.00 | 0.20 (0.4x) | 0.04 (0.3x) | 0.05 (0.2x) | 0.05 (0.1x) | 0.44 (1.4x, p 0.068) |

Within ±10 s: instagram → facebook 0.47 (1.9x, p 0.037), instagram → instagram 2.2x, mozilla 1.6x, x 1.4x (all p < 0.01).

**3. The facebook flows one by one** (from the script's table): they come in close pairs (000799/000809 1.1 s apart,
001145/001168 2.7 s, 000610/000617 and 001324/001331 about 14 s), two start 0.0 s and 0.1 s from an Instagram flow
(000610, 001324), and one 0.0 s from a Mozilla flow (000024).

## Caveats

- The co-start test was designed after the pre-registered test came back unclear. It has 72 cells (36 pairs × 2 windows),
  so a few p < 0.05 cells are expected by chance. The instagram → facebook cell is the one hypothesis C names in advance,
  which weakens but does not remove that concern.
- facebook → instagram (the other direction) is enriched (1.2x at 2 s, 1.6x at 10 s) but not significant: only 11 flows.
- Test flows are missing from the timeline, so some neighbours are unseen.
- "Labelled facebook while Instagram starts a connection at the same moment" fits C, and it also fits someone switching
  between the two apps quickly. Only the organisers can rule that out.

## Decision

Measurement only. The labelling rule is **not proven**, but the evidence leans toward **C (destination)** for facebook:

- No facebook time blocks exist (A and B predict them).
- Every app opens its connections in bursts: Instagram flows start together with Instagram flows (5.1x), Mozilla with
  Mozilla (3.0x), X with X (2.1x). **Facebook is the only other class that starts together with Instagram (2.9x)**, and it
  is depleted next to google, mozilla, x and youtube. That is what one trigger, the Instagram app, opening connections to
  both Instagram and Facebook servers would look like.

A side finding: **google does not cluster with itself at all (1.0x) and is spread over the whole capture.** That is how a
background service looks, not how an app session looks. It fits "google" also being a destination label (Google servers
contacted by the phone and by other apps), which would explain part of the google ↔ youtube confusion (161 CV errors).

## Next

- The organisers' answer on how flows were labelled is now the most valuable open item; send it with the question on
  reading server names in our own captures (needed to label them the same way).
- If C holds, session-labelled captures would mislabel Meta background flows. The capture pilot's stop rule already
  checks this, but labelling our own captures by destination needs the organisers' permission first.
- A google-as-background-service check (where google flows sit relative to YouTube and Firefox bursts) could be a follow-up.
