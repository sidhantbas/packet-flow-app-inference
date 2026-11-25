"""Experiment 023: session context for Task 1.

84% of flows start within 5 s of another flow: apps open bursts of connections. For each flow, describe the
other flows (all 411 Task 1 flows, feature files only, no labels) starting within ±w seconds: count, fraction UDP,
median log bytes down/up, median mean packet size down, median log duration. Added to the Task 1 champion's
34-column part (KeepClassBlend keeps the 17-column Facebook decisions). Runs cv_seeds 2026-2030 in one go.
"""
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from cv import DATA, TASKS, evaluate, task1_with_prefix_features
from models import task1_model
from runlog import load_champions, load_index, record_run

T1 = TASKS[0]
FILES = [f"task1_static/{s}_features.csv" for s in ("train", "validation", "test")]
ALL = pd.concat([pd.read_csv(DATA / f) for f in FILES], ignore_index=True)


def context_table(windows=(5, 30)):
    t = ALL.start_rel.values
    udp = (ALL.transport == "udp").values.astype(float)
    lbd, lbu = np.log1p(ALL.bytes_down.values), np.log1p(ALL.bytes_up.values)
    mpd, ldur = ALL.mean_pkt_size_down.values, np.log1p(ALL.duration.values)
    rows = []
    for i in range(len(ALL)):
        r = {}
        for w in windows:
            m = np.abs(t - t[i]) <= w
            m[i] = False
            n = m.sum()
            r[f"ctx{w}_n"] = n
            r[f"ctx{w}_udp"] = udp[m].mean() if n else -1
            r[f"ctx{w}_lbd"] = np.median(lbd[m]) if n else -1
            r[f"ctx{w}_lbu"] = np.median(lbu[m]) if n else -1
            r[f"ctx{w}_mpd"] = np.median(mpd[m]) if n else -1
            r[f"ctx{w}_ldur"] = np.median(ldur[m]) if n else -1
        rows.append(r)
    return pd.DataFrame(rows, index=ALL.flow_id.values)


CTX = context_table()


def with_context(X):
    B = task1_with_prefix_features(X)
    C = CTX.loc[X.flow_id.values].reset_index(drop=True)
    return pd.concat([B, C], axis=1)


with_context.extra_data = task1_with_prefix_features.extra_data + ["task1_static/test_features.csv"]

if __name__ == "__main__":
    refs = {e["name"]: e["run_id"] for e in load_index() if e["experiment"] == "022"}
    refs_by_seed = {2026: load_champions()[T1]["run_id"], 2027: refs["t1_champion_s2027"], 2028: refs["t1_champion_s2028"],
                    2029: refs["t1_champion_s2029"], 2030: refs["t1_champion_s2030"]}
    # confirmation seeds compare with the champion *model* re-run on those folds
    for seed, ref in refs_by_seed.items():
        if seed != 2026:
            t0 = datetime.now(timezone.utc)
            ref = record_run("023", f"t1_champion022_s{seed}", {T1: evaluate(T1, task1_with_prefix_features, task1_model, cv_seed=seed)},
                             reference=None, model_factory=task1_model, question=f"Reference: 022 task 1 model, cv_seed {seed}.",
                             config={"model": "task1_model", "cv_seed": seed}, started=t0)
        t0 = datetime.now(timezone.utc)
        record_run("023", f"t1_context_s{seed}", {T1: evaluate(T1, with_context, task1_model, cv_seed=seed)}, reference=ref,
                   model_factory=task1_model, feature_fn=with_context,
                   question=f"Task 1 + session context (cv_seed {seed})?",
                   config={"model": "task1_model", "features": "022 + context(5s, 30s)", "cv_seed": seed}, started=t0)
