"""Experiment 127: build an information-only, count-guided Meta candidate file (user request 2026-10-21: "build the submission file
in json format, and put the instagram and facebook flow order accordingly, on your own instinct").

Command: .venv/bin/python src/exp127_count_guided_candidate.py
Rule (fixed before building; it is rule D of experiment 099, applied to the current production file):
  Task 1: E = round(81 x instagram share of the 330 labelled flows); k = max(0, E - production's instagram count); the k test flows
          production does not call instagram with the highest instagram score s_ig (099's three-expert mean, saved in
          experiments/099_evidence/test_scores_task1_static.csv) become instagram.
  Task 2: production unchanged (014).
Writes submissions/candidate-127-meta-count-guided/{submission.json, submission.zip, comparison.json}. Uses no test labels, no test
label_counts, no leaderboard score. Not uploaded: the model behind it has not passed rule v2 (099 D: Δ -0.0169 in CV).
"""
import json
import subprocess
from pathlib import Path

import pandas as pd

from cv import load_task
from make_submission import TASKS, check, write_submission

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "submissions/production-100-cross-task/submission.json"
SCORES = ROOT / "experiments/099_evidence/test_scores_task1_static.csv"
OUT = ROOT / "submissions/candidate-127-meta-count-guided"
T1 = "task1_static"


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
    _, y = load_task(T1)
    n = len(preds[T1])
    E = int(round(n * (y == "instagram").mean()))
    have = sum(v == "instagram" for v in preds[T1].values())
    k = max(0, E - have)
    S = pd.read_csv(SCORES)
    S = S[S.flow_id.map(preds[T1]) != "instagram"].sort_values("s_ig", ascending=False)
    flips = [{"flow_id": r.flow_id, "production": preds[T1][r.flow_id], "candidate": "instagram", "s_ig": round(r.s_ig, 3)}
             for r in S.head(k).itertuples()]
    for f in flips:
        preds[T1][f["flow_id"]] = "instagram"
    for t in TASKS:
        check(preds[t], t)
    OUT.mkdir(parents=True, exist_ok=True)
    write_submission(preds, OUT / "submission.json", OUT / "submission.zip")
    ups = uploads()
    diff = {u: {t: sum(preds[t][i] != p[t].get(i) for i in preds[t]) for t in TASKS} for u, p in sorted(ups.items())}
    counts = {t: pd.Series(list(preds[t].values())).value_counts().to_dict() for t in TASKS}
    res = {"rule": "099 rule D on production 100 (Task 1); Task 2 production", "expected_instagram": E, "production_instagram": have,
           "k": k, "flips": flips, "predicted_counts": counts,
           "differs_from_uploads": diff, "uploads_missing": sorted(set(range(1, 10)) - set(ups)),
           "cv_evidence": "099 D (cv_seed 2026): flips right 27% (12 of 44), paired Δ macro F1 -0.0169, 7 W / 20 L / 23 T"}
    (OUT / "comparison.json").write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
