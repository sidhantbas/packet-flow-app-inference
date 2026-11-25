"""Flow-level paired check for Facebook/Instagram-targeted Task 1 changes (pre-registered in experiment 067).

Usage: python src/flowcheck.py OLD_RUN[,OLD_RUN...] NEW_RUN[,NEW_RUN...] [--apps a,b] [--task TASK] [--out FILE.md]
Pairs runs seed by seed (same folds). Per facebook/instagram flow: share of repeats right (old vs new), averaged per flow;
McNemar exact test on flows whose majority correctness differs; paired bootstrap over flows (2,000 resamples, the same
resample for every repeat and seed) of the facebook and instagram F1 differences with a 95% interval. Reading: an interval
that crosses zero is "unproven". Evidence only; the adoption rule (rule v2) is unchanged.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parent.parent
TASK = "task1_static"
APPS = ("facebook", "instagram")


def load(runs, task=TASK):
    return [pd.read_csv(ROOT / "results" / r / task / "oof.csv") for r in runs]


def f1(y, p, c):
    tp = ((y == c) & (p == c)).sum()
    d = (y == c).sum() + (p == c).sum()
    return 2 * tp / d if d else 0.0


def main(old_runs, new_runs, out=None, apps=APPS, task=TASK):
    O, N = load(old_runs, task), load(new_runs, task)
    for a, b in zip(O, N):
        assert (a.flow_id.values == b.flow_id.values).all() and (a.fold.values == b.fold.values).all(), "runs must share folds"
    old, new = pd.concat(O, ignore_index=True), pd.concat(N, ignore_index=True)
    old["ok"], new["ok"] = old.y_true == old.y_pred, new.y_true == new.y_pred
    so, sn = old.groupby("flow_id").ok.mean(), new.groupby("flow_id").ok.mean()
    truth = old.groupby("flow_id").y_true.first()
    lines = [f"Flow-level paired check: old {','.join(old_runs)} vs new {','.join(new_runs)}", ""]
    rows = []
    for fid in truth[truth.isin(apps)].index:
        a, b = so[fid], sn[fid]
        status = "fixed" if a < 0.5 <= b else "broken" if b < 0.5 <= a else "unchanged"
        rows.append((truth[fid], fid, a, b, status))
    lines += ["| app | flow | old right | new right | majority |", "|---|---|---:|---:|---|"]
    lines += [f"| {t} | {f} | {a:.2f} | {b:.2f} | {s} |" for t, f, a, b, s in sorted(rows)]
    fixed = sum(r[4] == "fixed" for r in rows)
    broken = sum(r[4] == "broken" for r in rows)
    pv = binomtest(fixed, fixed + broken, 0.5).pvalue if fixed + broken else 1.0
    lines += ["", f"McNemar ({"/".join(apps)} flows, majority correctness): fixed {fixed}, broken {broken}, exact p = {pv:.3f}"]
    flows = truth.index.values
    pos = {f: i for i, f in enumerate(flows)}
    oi, ni = old.flow_id.map(pos).values, new.flow_id.map(pos).values
    yo, po, pn = old.y_true.values, old.y_pred.values, new.y_pred.values
    rng = np.random.default_rng(0)
    point = {c: f1(yo, pn, c) - f1(yo, po, c) for c in apps}
    boots = {c: [] for c in apps}
    for _ in range(2000):
        w = np.bincount(rng.integers(0, len(flows), len(flows)), minlength=len(flows))
        wo = w[oi]
        for c in apps:
            def wf1(p):
                tp = (wo * ((yo == c) & (p == c))).sum()
                d = (wo * (yo == c)).sum() + (wo * (p == c)).sum()
                return 2 * tp / d if d else 0.0
            boots[c].append(wf1(pn) - wf1(po))
    for c in apps:
        lo, hi = np.percentile(boots[c], [2.5, 97.5])
        reading = "unproven (interval crosses zero)" if lo <= 0 <= hi else ("better" if lo > 0 else "worse")
        lines.append(f"{c} F1 difference (new - old): {point[c]:+.3f}, 95% bootstrap interval [{lo:+.3f}, {hi:+.3f}] -> {reading}")
    text = "\n".join(lines)
    print(text)
    if out:
        Path(out).write_text(text + "\n")


if __name__ == "__main__":
    a = sys.argv[1:]
    out = a[a.index("--out") + 1] if "--out" in a else None
    apps = tuple(a[a.index("--apps") + 1].split(",")) if "--apps" in a else APPS
    task = a[a.index("--task") + 1] if "--task" in a else TASK
    main(a[0].split(","), a[1].split(","), out, apps, task)
