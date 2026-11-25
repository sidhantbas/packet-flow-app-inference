"""Experiment 047: is Task 1's Facebook weakness a model problem or a data problem? (measurement only)

Command: .venv/bin/python src/exp047_model_or_data.py
Items of a user-supplied "evidence it's a model problem" checklist that earlier runs do not already answer:
  1. Memorisation: production fitted on the 11 facebook flows + 40 random others, scored on those same rows.
  2. Fit vs held-out: production on the first 2 repeats of the default folds (10 folds); facebook F1 on the training rows
     vs the held-out rows of each fold.
  5. Separability: probes on the 17 Task 1 columns (log1p + standardised) under the default 50-fold CV, recorded as runs:
     1-NN, 5-NN (distance-weighted) and balanced logistic regression. Plus, on all 330 flows, how many of each facebook
     flow's 5 nearest neighbours are facebook.
"""
from datetime import datetime, timezone

import numpy as np
from sklearn.metrics import f1_score, recall_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from cv import CV_SEED, TASK_FEATURES, basic_features, evaluate, load_task
from models import TASK_MODELS, knn, logreg
from runlog import record_run

TASK, FB = "task1_static", "facebook"
Xr, y = load_task(TASK)
X = TASK_FEATURES[TASK](Xr)
yv = np.asarray(y, dtype=object)

print("## 1. Memorisation (11 facebook + 40 others, scored on the training rows)")
rng = np.random.default_rng(0)
idx = np.concatenate([np.flatnonzero(yv == FB), rng.choice(np.flatnonzero(yv != FB), 40, replace=False)])
m = TASK_MODELS[TASK](0).fit(X.iloc[idx], y.iloc[idx])
p = m.predict(X.iloc[idx])
print(f"facebook recall {recall_score(yv[idx] == FB, p == FB):.3f}, F1 {f1_score(yv[idx] == FB, p == FB):.3f}, "
      f"accuracy {np.mean(p == yv[idx]):.3f}")

print("\n## 2. Facebook F1 on training rows vs held-out rows (production, 10 folds)")
tr_f1, te_f1 = [], []
for i, (tr, te) in enumerate(RepeatedStratifiedKFold(n_splits=5, n_repeats=2, random_state=CV_SEED).split(X, y)):
    m = TASK_MODELS[TASK](i).fit(X.iloc[tr], y.iloc[tr])
    tr_f1.append(f1_score(yv[tr] == FB, m.predict(X.iloc[tr]) == FB))
    te_f1.append(f1_score(yv[te] == FB, m.predict(X.iloc[te]) == FB, zero_division=0))
print(f"train facebook F1 {np.mean(tr_f1):.3f} (min {np.min(tr_f1):.3f}); held-out {np.mean(te_f1):.3f} "
      f"(std {np.std(te_f1, ddof=1):.3f})")

print("\n## 5a. Probes on the 17 Task 1 columns (50-fold CV, recorded runs)")
probes = {"knn1": lambda s: knn(s, k=1), "knn5": lambda s: knn(s, k=5), "logreg": lambda s: logreg(s)}
for name, f in probes.items():
    t0 = datetime.now(timezone.utc)
    r = evaluate(TASK, basic_features, f)
    yt, yp = r["y_true"], r["y_pred"]
    print(f"{name}: macro {r['macro_mean']:.3f}, facebook recall {recall_score(yt == FB, yp == FB):.3f}, "
          f"F1 {r['per_class_mean'][FB]:.3f}; facebook predicted as {dict(zip(*np.unique(yp[yt == FB], return_counts=True)))}")
    record_run("047", name, {TASK: r}, model_factory=f, feature_fn=basic_features, reference=None,
               question=f"Task 1: how separable is facebook for a {name} probe on the 17 Task 1 columns?",
               config={"model": name, "cv_seed": CV_SEED, "features": "basic_features"}, started=t0)

print("\n## 5b. Facebook neighbourhoods (all 330 flows, 17 Task 1 columns, log1p + standardised)")
Z = StandardScaler().fit_transform(np.log1p(basic_features(Xr).clip(lower=0)))
nn = NearestNeighbors(n_neighbors=6).fit(Z)
_, nb = nn.kneighbors(Z[yv == FB])
same = (yv[nb[:, 1:]] == FB).sum(axis=1)
print(f"facebook neighbours among the 5 nearest, per facebook flow: {sorted(same.tolist())}; "
      f"mean share {same.mean() / 5:.2f} (facebook share of all flows {np.mean(yv == FB):.3f})")
print("neighbour labels:", dict(zip(*np.unique(yv[nb[:, 1:]], return_counts=True))))
