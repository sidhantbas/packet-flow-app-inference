"""One-time migration (2026-10-12, repo phase 1): give every experiment log the same machine-readable `experiment:` block in
its YAML front matter, so EXPERIMENTS.md can be generated (src/build_experiments_index.py).

- Logs that already have front matter get the block appended inside it.
- Logs without front matter (001-052) get a front matter with title (their H1), created (their **Date:** line), creator, and
  description (their **Question:** line, when present), plus the block.
- The log body is never changed; the script checks this and that every front matter parses as YAML.

Verdicts were transcribed from each log's own results/decision sections (and BACKLOG.md); nothing new is claimed here.
Usage: .venv/bin/python src/migrate_experiment_frontmatter.py [--dry-run]
"""
import datetime
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments"
T1, T2, BOTH = ["task1"], ["task2"], ["task1", "task2"]

# id: (tasks, lever, status, verdict, production role or None)
META = {
    "001": (BOTH, "evaluation", "measured", "RandomForest baseline on the single validation split: Task 1 0.713, Task 2 0.743 (72.8 points); superseded by repeated CV in 002", None),
    "002": (BOTH, "evaluation", "measured", "Repeated stratified 5x10 CV introduced (RF: Task 1 0.733, Task 2 0.676); start_rel adds +0.003 / +0.013, treated as recording-time leakage and excluded", None),
    "003": (BOTH, "model", "rejected", "balanced_subsample, log1p, ExtraTrees or LightGBM alone, facebook/instagram duplication: all within noise; RF stays the default", None),
    "004": (BOTH, "model", "adopted", "SoftVote (RF + ExtraTrees + LightGBM): Task 1 0.771 (+0.038, 34/50, adopted by explicit decision in 005); per-class multipliers hurt in all 4 settings; Task 2 identical-vector ceiling 0.930", "SoftVote base learner of every model"),
    "005": (BOTH, "submission", "submission", "First complete submission pipeline (SoftVote, both tasks): official-scorer check, seed stability, compute cost", None),
    "006": (BOTH, "tooling", "tooling", "Run logging (record_run: manifests, hashes, paired comparison, checks, verify) reproduces 004 exactly; SoftVote becomes champion for both tasks", None),
    "007": (T2, "features", "adopted", "Task 2 without the 5 timing columns: +0.051 (40/50, every class up), confirmed on seeds 2027/2028; dropping min_iat in Task 1 has no effect", "Task 2 features: 12 no-timing columns (cv.no_timing_features)"),
    "008": (BOTH, "features", "rejected", "Five ratio families: no effect on Task 1; Task 2 -0.05 to -0.06 for relative timing, rates and burst density", None),
    "009": (BOTH, "model", "inconclusive", "CatBoost alone, categorical, or as a 4th member: inconclusive; unweighted CatBoost best on Task 2 (+0.015, 27/50), a lead that class weights may hurt Task 2", None),
    "010": (BOTH, "diagnostic", "measured", "Permutation importance over 50 folds: timing is Task 1's facebook signal; Task 2 relies mostly on upstream columns", None),
    "011": (T2, "diagnostic", "measured", "Task 2 burst_count drop -0.001 (kept); 74% of held-out flows have an exact training twin (96% right); 68% of errors are on never-seen vectors; start_rel alone scores 0.51", None),
    "012": (BOTH, "imbalance", "measured", "No class weights: Task 1 -0.014 (facebook -0.090) so balanced weights stay; Task 2 +0.012 (24/5/21, instagram +0.075), the lead for 014", None),
    "013": (BOTH, "hierarchy", "rejected", "Google-vs-youtube specialist: |delta| <= 0.005; the 6-class model already separates the pair about as well as a dedicated one (AUC 0.89 / 0.92)", None),
    "014": (BOTH, "hierarchy", "adopted", "Unweighted facebook/instagram stage: Task 2 +0.018 (18/1/31; facebook +0.026, instagram +0.083), rule v2 on 3 seeds; Task 1 hurts facebook (-0.05 to -0.08)", "Task 2 model (models.task2_model)"),
    "015": (T2, "hierarchy", "rejected", "Timing-aware mozilla/x specialist: pair AUC 0.945 -> 0.976 but delta ~0; it only swaps errors inside the pair", None),
    "016": (BOTH, "model", "inconclusive", "Bigger leaves hurt (memorising exact twins is right; Task 2 -0.02); LR + kNN members +0.006 on Task 2 (near-miss); kNN costs Task 1 facebook -0.075", None),
    "017": (T2, "model", "inconclusive", "Novelty gating (smooth members only for unseen vectors) equals 016 exactly: +0.006, near-miss", None),
    "018": (BOTH, "model", "rejected", "Ensemble settings sweep (max_features, LightGBM leaves, 1000 trees): all within +-0.011; 1000 trees failed confirmation", None),
    "019": (BOTH, "model", "rejected", "Stacking with a learned logistic combiner: facebook -0.17 to -0.24 (inner folds hold about 5 facebook flows)", None),
    "020": (T2, "features", "rejected", "Exact individual packet sizes where determined: no change; every Task 2 flow has exactly 5 packets", None),
    "021": (BOTH, "diagnostic", "measured", "The validation gap is facebook (Task 1 validation facebook F1 0.00: 3 long TCP flows unlike train); a TCP-signature variant hurts facebook (-0.046)", None),
    "022": (T1, "features", "adopted", "Task 1 + the 17 first-5-packet statistics (KeepClassBlend, facebook calls of the 17-column model kept): 0.807 (+0.036), rule v2 on 5 seeds", "Task 1 whole-flow expert with the first-5-packet columns"),
    "023": (T1, "features", "rejected", "Concurrent-flow context (other flows starting within +-5 / +-30 s): delta -0.010 to +0.002 on 5 seeds; uses capture time, later ruled off-limits (039)", None),
    "024": (BOTH, "model", "inconclusive", "TabPFN v2: alone worse (Task 1 0.769, facebook -0.21; Task 2 0.734); as a 3rd Task 1 member +0.014 to +0.018 on 5 seeds but fails rule v2 on 2028/2029; pretrained, excluded", None),
    "025": (BOTH, "data", "rejected", "Self-training on held-out + test features (p >= 0.9): Task 1 -0.006, Task 2 0.000; confident pseudo-labels were already right", None),
    "026": (T1, "model", "unfinished", "Fine-tuned TabPFN: the seed-2028 confirmation was stopped by the user and never rerun", None),
    "027": (BOTH, "features", "measured", "Charles's plan A-D run locally: timing-derived prefix features (B, C) hurt; family A helps his ExtraTrees on Task 2 (+0.007 to +0.012); nothing changes our submission", None),
    "028": (T1, "model", "adopted", "Two experts (whole flow + opening), Meta decided by the whole-flow expert: 0.817, +0.005 to +0.013 on 5 seeds but 58-65% wins; adopted as a documented exception", "Task 1 two experts (whole flow + opening)"),
    "029": (T1, "features", "rejected", "Behaviour concepts (flags -0.000; KMeans kinds of run -0.008): every app makes every kind of run", None),
    "030": (T1, "features", "rejected", "Exact rest-of-flow statistics as columns: -0.0095 added, -0.040 replacing the opening columns (later used as an expert in 065)", None),
    "031": (BOTH, "diagnostic", "measured", "Error audit: most google/youtube errors have a nearest training row of the predicted app; decision-rule headroom <= 3 (Task 1) and <= 6 (Task 2) errors in 3,300; no candidate", None),
    "032": (BOTH, "model", "rejected", "App signatures (instagram bursts AUC 0.91 ...) are real but moderate; naive Bayes on behaviour levels 0.64 / 0.53 alone, -0.040 / -0.007 as a member", None),
    "033": (BOTH, "decision", "rejected", "Gated behaviour hybrid (lambda, tau by nested CV): Task 1 -0.012, Task 2 -0.002; the inner selection picks up luck", None),
    "034": (T1, "hierarchy", "adopted", "Meta gate (Meta vs rest first, then facebook vs instagram by the whole-flow expert): 0.828, facebook 0.59 -> 0.67, instagram -0.029; adopted as a decision-theoretic exception", "Task 1 Meta gate"),
    "035": (T1, "hierarchy", "rejected", "H1 (trust exact opening twins): -0.0345; twin leakage: the near-identical facebook pair in one fold drops facebook F1 0.674 -> 0.521", None),
    "036": (T1, "evaluation", "adopted", "Test flows meet near-twins more often than CV held-out flows (18.5% vs 11.8%), so normal CV mirrors the test; twin-aware CV costs ~0.05 for all models; scoped H1 passes rule v2 on 6 split sets", "Scoped exact-opening override (via 089)"),
    "037": (T1, "hierarchy", "rejected", "Nearest-twin override: production already predicts every near-twin's label; 0 test changes; dropped", None),
    "038": (BOTH, "diagnostic", "measured", "Field audit: no unused signal left (only identifiers, capture time, a constant port and forbidden test counts); Task 2 outputs inside Task 1 hurt (-0.006 / -0.013)", None),
    "039": (BOTH, "diagnostic", "measured", "Capture order follows start_rel exactly; 78% same-app runs vs 42.5% random, but kNN on order scores 0.50 and costs production -0.040; treated as off-limits", None),
    "040": (T1, "evaluation", "measured", "81-flow test noise: the same model scores 0.737-0.917 (5th-95th); our 0.787 sits near the 21st percentile, the leader's 0.94 near the 98.7th; one facebook flow = 2-4 points", None),
    "041": (BOTH, "data", "measured", "Own captures feasibility: no-go at the time; all 21 feature formulas decoded; 7 facebook/instagram traffic types; labels look destination-based", None),
    "042": (T1, "tooling", "tooling", "Capture pipeline: pcap -> organiser features for both tasks, gates 1 and 2, self-test", None),
    "043": (BOTH, "decision", "rejected", "Push borderline flows to facebook (top-k from the training share, pair threshold): Task 2 worse (instagram -0.08), Task 1 inconclusive", None),
    "044": (T1, "imbalance", "rejected", "Facebook sub-type classes merged at prediction: -0.0126 (9/23), facebook -0.066", None),
    "045": (T1, "imbalance", "rejected", "Formula-respecting synthetic facebook flows (SMOTE-style): -0.0108, facebook -0.058 (precision falls, recall unchanged)", None),
    "046": (BOTH, "diagnostic", "measured", "Gap to the leader (84.62 vs 93.19): 89% in Task 1; errors involving facebook or instagram are the largest target; no single fix closes it", None),
    "047": (T1, "diagnostic", "measured", "Model or data? 5 of 9 checklist items point to the data: verdict scarcity (11 facebook flows, 5 traffic types, no cluster of their own)", None),
    "048": (T1, "diagnostic", "measured", "Facebook vs instagram separable beyond chance (F1 0.66, p 0.01); merged Meta class F1 0.88-0.91; facebook learning curve still rising", None),
    "049": (T1, "diagnostic", "measured", "The facebook vs instagram signal is behaviour (volume, rates), not session length; the opening alone is at chance", None),
    "051": (BOTH, "diagnostic", "measured", "Labelling rule: no facebook time blocks; facebook starts together with instagram (2.9x); leans toward destination-based labels, not proven", None),
    "052": (T1, "data", "measured", "iPhone capture pilot: gate 1 pass, gate 2 fail (AUC 0.993); the pilot's Wi-Fi blocked QUIC for Instagram/YouTube; not usable for training", None),
    "053": (T1, "data", "measured", "TCP flow start: dropping the handshake moves openings toward the dataset's 3 up / 2 down (TVD 0.62 -> 0.26) but misses the frozen 0.15 rule; extractor default unchanged", None),
    "054": (T1, "data", "measured", "Independent clean-room extraction matches all 11,424 values; captured Meta packet sizes mostly match, durations, gaps and bursts do not", None),
    "055": (T1, "data", "measured", "20-minute cellular sessions: closer, but gates 1 and 2 fail (AUC 0.957); QUIC first-packet sizes differ (1242/1274 vs 1363-1381 B)", None),
    "056": (T1, "data", "rejected", "Captured flows in Task 1 training folds: -0.084 / -0.072; facebook -0.30 to -0.38", None),
    "057": (T1, "data", "rejected", "Captured flows only in the facebook/instagram decision (-0.043) or as a 10% dose (-0.026): worse", None),
    "058": (T1, "data", "rejected", "Captured flows as a never-predicted 'other' class: -0.0003 / -0.0077; the damage goes but so does any gain", None),
    "059": (T1, "data", "measured", "Android through the Mac's shared Wi-Fi: TCP opening shapes match (TVD 0.11) but QUIC first packets 1274/1294 B vs 1363-1381 B; captures stop", None),
    "060": (T2, "model", "rejected", "Unweighted CatBoost, SoftVote + CatBoost, family A columns (each with the 014 stage): -0.004 / -0.001 / -0.001", None),
    "061": (T1, "decision", "rejected", "F1-optimal thresholds (t = F/2 and F/4 from inner CV): -0.0011 / +0.0008, inconclusive", None),
    "062": (T1, "decision", "inconclusive", "F/2 thresholds among non-Meta apps only: positive on 5/5 seeds (mean +0.003) but BETTER on 3/5; not adopted", None),
    "063": (T1, "data", "rejected", "Android captures in training -0.059; same-label-filtered captures -0.010; capture training closed", None),
    "064": (T1, "model", "rejected", "Third expert (kNN, logistic regression, both): -0.006 / -0.015 / -0.019; weak learners on the same columns add noise", None),
    "065": (T1, "model", "adopted", "Rest-of-flow expert as a third expert in the Meta-gate model: +0.0054 at seed 2026 (near-miss); later part of the 089 bundle", "Rest-of-flow expert (via 089)"),
    "066": (T1, "model", "adopted", "Five-seed check of the rest-of-flow expert: delta > 0 on all seeds (mean +0.0066, 62.2% wins); uploaded as a candidate (about 86); later part of 089", "Rest-of-flow expert (via 089)"),
    "067": (T1, "decision", "rejected", "Tuned facebook threshold (chosen cutoff 0.20-0.80 across folds) and a twins-to-facebook rule: no gain", None),
    "068": (T1, "diagnostic", "measured", "Facebook vs google: identical opening fingerprints, 3 vs 62 flows; closed as irreducible", None),
    "069": (T1, "diagnostic", "measured", "Google vs youtube errors by opening type: TCP 43%, mixed QUIC 32%, clean QUIC 25%", None),
    "070": (BOTH, "features", "rejected", "Bounds on the largest outgoing packet: youtube up on every seed but facebook/mozilla down; macro flat (+-0.004)", None),
    "071": (BOTH, "hierarchy", "rejected", "Google-vs-youtube specialist with the bounds: Task 1 -0.0055, Task 2 +0.0009; fails at seed 2026", None),
    "072": (T1, "diagnostic", "measured", "Instagram vs youtube errors come from 4 flows; closed as irreducible", None),
    "073": (T1, "diagnostic", "measured", "Google vs mozilla errors come from 10 mostly-TCP flows; at most about 0.2 points recoverable; closed", None),
    "074": (BOTH, "diagnostic", "measured", "65% (Task 1) and 81% (Task 2) of errors are on flows whose nearest training flow belongs to another app; modelling ceiling about +1.8 / +1.6 CV points", None),
    "075": (T1, "decision", "inconclusive", "Rest-of-flow expert + non-Meta thresholds: mean +0.0061 vs production but no gain over the rest-of-flow expert alone", None),
    "076": (T1, "diagnostic", "measured", "View screen: the opening fingerprint fixes 51% more production errors than the opening view at equal breaks", None),
    "077": (T1, "model", "inconclusive", "Fingerprint expert alone WORSE on 5 seeds; fingerprint + rest-of-flow experts BETTER on 4/5; same test file as 87.77", None),
    "078": (T1, "model", "inconclusive", "TabPFN as an extra expert (check only): mean +0.0027, no seed BETTER; pretrained, excluded", None),
    "079": (BOTH, "diagnostic", "measured", "Pipeline audit: Task 2's loss is mostly irreducible (floor 9.19 of 11.38 points); Task 1 is data-starved; all model-limited cells together are about +1 CV point", None),
    "080": (T1, "evaluation", "measured", "All CV-supported models agree on 78 of 81 test flows; no new submission justified", None),
    "081": (T1, "imbalance", "rejected", "Few-shot metric learning (NCA + kNN) for facebook: facebook F1 0.24 vs 0.69; gate failed", None),
    "082": (T1, "imbalance", "rejected", "Undersampling-ensemble facebook detector: macro -0.005; 10 of 11 rescues wrong; gate failed", None),
    "083": (T1, "hierarchy", "adopted", "Google-vs-instagram verifier for instagram calls: rule v2 BETTER on 3 seeds (+0.0016 to +0.0045); test file unchanged; part of 084", "Google-vs-instagram verifier (via 084)"),
    "084": (T1, "hierarchy", "adopted", "Adds a google-vs-x verifier for x calls (ALL = 083 + VX): BETTER on all 5 seeds (mean +0.0050), facebook unchanged; production 9-10 Oct (88.11)", "Google-vs-x verifier; Task 1 production 9-10 Oct"),
    "085": (BOTH, "hierarchy", "rejected", "Verifier sweep over 9 more separable pairs: none passes; Task 2 mozilla verifier 55 W / 0 L but BETTER on 4/5", None),
    "086": (BOTH, "hierarchy", "rejected", "Google/youtube sub-types and TCP/QUIC desks: Task 1 -0.015 to -0.022, Task 2 within +-0.002", None),
    "087": (T1, "hierarchy", "adopted", "The Meta gate may rescue flows into facebook only: BETTER on 3/5 seeds (mean +0.0020, instagram up); later part of 089", "Facebook-only gate rescue (via 089)"),
    "088": (BOTH, "decision", "rejected", "Expected-macro-F1 batch labelling: Task 1 -0.0015 (23 W / 23 L), Task 2 -0.0051", None),
    "089": (T1, "model", "adopted", "Near-miss bundle (rest-of-flow expert + facebook-only rescue + scoped exact-opening override): BETTER on 5 never-used seeds (mean +0.0141); Task 2 bundle fails", "Task 1 production since 10 Oct (models.task1_bundle)"),
    "090": (BOTH, "features", "measured", "Stamp catalogue: TCP opening decode verified 100/102; no Task 1 gain; Task 2 facebook/instagram AUC +0.016; 4 of 11 facebook flows carry a facebook-only stamp", None),
    "091": (T1, "data", "rejected", "Public 2026 Android dataset: 0% of its Meta QUIC first packets match the challenge signature; stopped before training", None),
    "092": (BOTH, "data", "rejected", "Confident-learning cleaning of training folds: -0.027 / -0.038; the removed rows are hard real examples", None),
    "093": (BOTH, "diagnostic", "measured", "Data-limited analysis: learning curve still rising (+3.6 points from 80% to 100%), label noise about 0; derivable features, self-training and constraints all tie", None),
    "094": (BOTH, "model", "rejected", "Seed-bagging the whole pipeline: no change (44-46 of 50 folds identical); nested feature selection -0.016", None),
    "095": (BOTH, "decision", "rejected", "The leader's described method simulated (calibration + count matching; test counts never read): every version below production", None),
    "096": (T2, "decision", "rejected", "Timing as a tie-breaker inside identical 12-feature groups: WORSE on 3 seeds and grouped folds, 0 errors corrected; Meta groups untestable", None),
    "097": (T1, "evaluation", "measured", "089 beats 084 on ordinary and twin-aware folds (+0.014 to +0.017); exact-opening override consistently useful; rest-of-flow expert and facebook-only rescue inconclusive by rule", None),
    "098": (T1, "diagnostic", "measured", "Facebook audit: 22 of 31 facebook errors have every expert wrong; no candidate justified; final file identical to the ranked entry", None),
}

LEVERS = {"evaluation", "features", "model", "imbalance", "hierarchy", "decision", "data", "diagnostic", "tooling", "submission"}
STATUSES = {"adopted", "inconclusive", "rejected", "measured", "tooling", "submission", "unfinished"}


def split_front(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.index("\n---\n", 4)
    return text[4:end], text[end + 5:]


def block(eid):
    tasks, lever, status, verdict, role = META[eid]
    assert lever in LEVERS and status in STATUSES, eid
    d = {"id": eid, "tasks": tasks, "lever": lever, "status": status, "verdict": verdict}
    if role:
        d["production"] = role
    return d


def main(dry):
    logs = sorted(EXP.glob("[0-9][0-9][0-9]_*.md"))
    assert {p.name[:3] for p in logs} == set(META), sorted({p.name[:3] for p in logs} ^ set(META))
    changed = 0
    for p in logs:
        eid, text = p.name[:3], p.read_text()
        fm, body = split_front(text)
        if fm is not None:
            data = yaml.safe_load(fm)
            if "experiment" in data:
                continue
            new_fm = fm.rstrip("\n") + "\n" + yaml.safe_dump({"experiment": block(eid)}, sort_keys=False, allow_unicode=True, width=1000)
        else:
            title = re.search(r"^# (.+)$", text, re.M).group(1).strip()
            date = re.search(r"\*\*Date:\*\*\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text).group(1)
            q = re.search(r"\*\*Question:\*\*\s*(.+)", text)
            d = {"title": title, "created": datetime.date.fromisoformat(date), "creator": "sidhantbas"}
            if q:
                d["description"] = re.sub(r"[`*]", "", q.group(1)).strip()
            d["experiment"] = block(eid)
            new_fm = yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=1000)
        new = "---\n" + new_fm.rstrip("\n") + "\n---\n" + (body if fm is not None else text)
        nfm, nbody = split_front(new)
        assert nbody == (body if fm is not None else text), eid
        parsed = yaml.safe_load(nfm)
        assert parsed["experiment"]["id"] == eid and parsed["title"], eid
        if not dry:
            p.write_text(new)
        changed += 1
    print(f"{'would update' if dry else 'updated'} {changed} of {len(logs)} logs")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
