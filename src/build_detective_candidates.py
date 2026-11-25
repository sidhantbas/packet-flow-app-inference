"""Detective candidates (user request 2026-10-14): five test files rebuilt from the leaderboard leaders' method notes, ranked by
expected leaderboard score rather than by rule v2. Not production, not uploaded; the upload decision stays with the user.

The clue they rest on: the Task 1 and Task 2 test files hold the same 81 flow ids, and the tasks share labels (train+validation
labels are identical per flow; 104: one prediction set gives identical fold scores in both tasks). Our Task 2 file (014) scored
0.905 on those flows, our Task 1 files 0.82-0.857. Task 1 may read the Task 2 files (allowed since 022; disclosed). Count
matching uses training class shares x 81 (largest remainder); the published test counts are never read (stratified split, and
104 measured +0.001 for disclosure over shares).

Views (fitted on train+validation, seed 0; Task 2 views read only Task 2 files):
  open    : Task 2 production model (014), 12 no-timing prefix-5 columns
  sig/iso : sigmoid / isotonic calibrated balanced SoftVote on those columns (102 arms F2S-S / F2I-S before counts)
  early   : balanced SoftVote on all 17 prefix-5 columns, with timing (104 arm E1S before counts)
  full    : sigmoid calibrated balanced SoftVote on the 17 Task 1 columns (Task 1 only)

Usage: .venv/bin/python src/build_detective_candidates.py      # writes submissions/detective-*/ and detective-summary.json
"""
import json
from collections import Counter
from pathlib import Path

import numpy as np

from cv import TASK_FEATURES, basic_features, load_task
from flowkit import from_spec
from flowkit.calibration import calibrated
from flowkit.counts import label_counts, quota_assign, share_counts
from make_submission import check, load_test, write_submission
from models import T1_COLS, SoftVote, task2_model

ROOT = Path(__file__).resolve().parent.parent
T1, T2 = "task1_static", "task2_realtime_prefix5"
UPLOADS = {6: "best-88.11-production-084", 7: "production-089-bundle", 8: "production-100-cross-task"}
CANDIDATES = {  # name: (Task 1 labels, Task 2 labels)
    "detective-1-flowlens-v8-twin": ("sig_counts", "sig_counts"),
    "detective-2-flowlens-v9-crossview": ("cross_counts", "sig_counts"),
    "detective-3-flowlens-isotonic-twin": ("iso_counts", "iso_counts"),
    "detective-4-rahmanij-twin": ("early_counts", "early_counts"),
    "detective-5-mirror-floor": ("open", "open"),
}


def labels():
    X2r, y = load_task(T2)
    y = np.asarray(y.values, dtype=object)
    X2t = load_test(T2)
    ids = list(X2t.flow_id)
    nt = TASK_FEATURES[T2]
    lab = {"open": np.asarray(task2_model(0).fit(nt(X2r), y).predict(nt(X2t)), dtype=object)}
    sig = from_spec("base=softvote,cal=sigmoid", seed=0).fit(nt(X2r), y)
    iso = from_spec("base=softvote,cal=isotonic", seed=0).fit(nt(X2r), y)
    early = from_spec("base=softvote", seed=0).fit(basic_features(X2r), y)
    classes = list(sig.classes_)
    counts = share_counts(classes, {c: n / len(y) for c, n in label_counts(y).items()}, len(ids))
    p_sig = sig.predict_proba(nt(X2t))
    lab["sig_counts"] = quota_assign(p_sig, classes, counts)
    lab["iso_counts"] = quota_assign(iso.predict_proba(nt(X2t)), classes, counts)
    lab["early_counts"] = quota_assign(early.predict_proba(basic_features(X2t)), classes, counts)

    X1r, y1 = load_task(T1)
    X1t = load_test(T1).set_index("flow_id").loc[ids].reset_index()
    f1, cols = TASK_FEATURES[T1], list(T1_COLS)
    full = calibrated(SoftVote(seed=0), "sigmoid", 0).fit(f1(X1r)[cols], np.asarray(y1.values, dtype=object))
    assert list(full.classes_) == classes
    lab["cross_counts"] = quota_assign((p_sig + full.predict_proba(f1(X1t)[cols])) / 2, classes, counts)
    return ids, lab, counts


def main():
    ids, lab, counts = labels()
    up = {k: json.loads((ROOT / "submissions" / v / "submission.json").read_text()) for k, v in UPLOADS.items()}
    floor = dict(zip(ids, lab["open"]))  # our Task 2 file: scored 0.905 on these 81 flows
    summary = {"training_share_counts": {c: int(n) for c, n in counts.items()}, "candidates": {}}
    for name, (a1, a2) in CANDIDATES.items():
        preds = {T1: dict(zip(ids, lab[a1])), T2: dict(zip(ids, lab[a2]))}
        for t in (T1, T2):
            check(preds[t], t)
        out = ROOT / "submissions" / name
        out.mkdir(exist_ok=True)
        write_submission(preds, out / "submission.json", out / "submission.zip")
        info = {"task1": a1, "task2": a2}
        for t in (T1, T2):
            info[t] = {"counts": dict(Counter(preds[t].values())),
                       "vs_0.905_file": {f: f"{floor[f]} -> {preds[t][f]}" for f in ids if floor[f] != preds[t][f]},
                       **{f"changed_vs_upload{k}": sum(u[t][f] != preds[t][f] for f in ids) for k, u in up.items()}}
        summary["candidates"][name] = info
        print(name, {t: (len(info[t]["vs_0.905_file"]), info[t]["changed_vs_upload6"]) for t in (T1, T2)})
    (ROOT / "submissions" / "detective-summary.json").write_text(json.dumps(summary, indent=2, default=int) + "\n")


if __name__ == "__main__":
    main()
