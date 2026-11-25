"""Experiment 128: build an information-only candidate file = upload 10 (candidate 127) with Task 2 from experiment 109's arm B
(user request 2026-10-21: "build the 109 B file").

Command: .venv/bin/python src/exp128_109b_candidate.py
Task 1: candidate 127's predictions, unchanged. Task 2: 109 B (`SelectSpecialist`, seed 0) fitted on the 330 labelled Task 2 flows
with 109's 30 Task 2 columns (12 production + 10 engineered + 8 decoded opening sizes), predicting the 81 test flows. Reads only
Task 2 files for Task 2. Writes submissions/candidate-128-109b-task2/{submission.json, submission.zip, comparison.json}.
Not uploaded: 109 B is BETTER on 3 of 5 fresh seeds (not 5), changes 1 test flow, and its decoded sizes await the condition-3 call.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from cv import load_task
from exp109_task2_first_packet_specialist import SelectSpecialist, task2_candidates
from make_submission import TASKS, check, load_test, write_submission

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "submissions/candidate-127-meta-count-guided/submission.json"
OUT = ROOT / "submissions/candidate-128-109b-task2"
T2 = "task2_realtime_prefix5"


def uploads():
    U = pd.read_csv(ROOT / "submissions/uploads.csv")
    out = {}
    for r in U.itertuples():
        f = str(r.file)
        if f.startswith("submissions/"):
            p = ROOT / f.split(" ")[0] / "submission.json"
            if p.exists():
                out[int(r.upload)] = json.loads(p.read_text())
        elif f.startswith("commit "):
            s = subprocess.run(["git", "show", f"{f.split()[1]}:submissions/submission.json"], cwd=ROOT, capture_output=True, text=True)
            if s.returncode == 0:
                out[int(r.upload)] = json.loads(s.stdout)
    return out


def main():
    base = json.loads(BASE.read_text())
    preds = {t: dict(base[t]) for t in TASKS}
    X_raw, y = load_task(T2)
    m = SelectSpecialist(seed=0).fit(task2_candidates(X_raw), np.asarray(y.values, dtype=object))
    Xt_raw = load_test(T2)
    p = np.asarray(m.predict(task2_candidates(Xt_raw)), dtype=object)
    changes = [{"flow_id": i, "upload_10": preds[T2][i], "candidate": v} for i, v in zip(Xt_raw.flow_id, p) if preds[T2][i] != v]
    preds[T2] = dict(zip(Xt_raw.flow_id, p))
    for t in TASKS:
        check(preds[t], t)
    OUT.mkdir(parents=True, exist_ok=True)
    write_submission(preds, OUT / "submission.json", OUT / "submission.zip")
    ups = uploads()
    res = {"base": "candidate 127 (upload 10)", "task2_model": "109 B SelectSpecialist(seed=0), 30 Task 2 columns",
           "specialist_columns": m.spec_cols_, "task2_changes_vs_upload_10": changes,
           "predicted_counts": {t: pd.Series(list(preds[t].values())).value_counts().to_dict() for t in TASKS},
           "differs_from_uploads": {u: {t: sum(preds[t][i] != q[t].get(i) for i in preds[t]) for t in TASKS} for u, q in sorted(ups.items())},
           "cv_evidence": "109 B on never-used seeds 2136-2140: mean Δ +0.0197, Δ > 0 on 5 of 5, BETTER on 3 of 5; grouped folds (117) "
                          "+0.031, BETTER 5 of 5, but a two-value size rule resting on two near-identical facebook pairs"}
    (OUT / "comparison.json").write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
