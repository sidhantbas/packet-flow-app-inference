"""Train the soft-voting ensemble per task on train+validation and write the test submission.
Features per task come from cv.TASK_FEATURES (task 2 drops timing since 007); models from
models.TASK_MODELS (task 2 adds a facebook/instagram specialist since 014).

Outputs submissions/submission.json (official JSON format) and submissions/submission.zip
(task1_static.csv, task2_realtime_prefix5.csv). Each task reads only from its own folder.
"""
import io
import json
import zipfile
from pathlib import Path

import pandas as pd

from cv import DATA, TASK_FEATURES, TASKS, load_task
from models import TASK_MODELS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "submissions"
ALLOWED = {"facebook", "google", "instagram", "mozilla", "x", "youtube"}
SEED = 0


def load_test(task):
    return pd.read_csv(DATA / task / "test_features.csv")


def fit_predict(task, train_splits=("train", "validation"), predict_split="test", seed=SEED):
    """Fit the task's model (models.TASK_MODELS) on `train_splits` of one task and predict `predict_split` of it."""
    X_raw, y = load_task(task, train_splits)
    features = TASK_FEATURES[task]
    model = TASK_MODELS[task](seed).fit(features(X_raw), y)
    X_pred = load_test(task) if predict_split == "test" else load_task(task, (predict_split,))[0]
    pred = model.predict(features(X_pred))
    return dict(zip(X_pred.flow_id, pred)), model


def check(predictions, task, split="test"):
    ids = set((load_test(task) if split == "test" else load_task(task, (split,))[0]).flow_id)
    assert set(predictions) == ids, f"{task}: missing {len(ids - set(predictions))}, extra {len(set(predictions) - ids)}"
    assert set(predictions.values()) <= ALLOWED, f"{task}: invalid labels {set(predictions.values()) - ALLOWED}"


def write_submission(preds, json_path, zip_path):
    json_path.write_text(json.dumps({t: dict(sorted(preds[t].items())) for t in TASKS}, indent=2) + "\n")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for t in TASKS:
            buf = io.StringIO()
            pd.DataFrame(sorted(preds[t].items()), columns=["flow_id", "app"]).to_csv(buf, index=False)
            zf.writestr(f"{t}.csv", buf.getvalue())


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    preds = {}
    for task in TASKS:
        preds[task], _ = fit_predict(task)
        check(preds[task], task)
        print(task, len(preds[task]), "predictions:", pd.Series(preds[task]).value_counts().to_dict())
    write_submission(preds, OUT / "submission.json", OUT / "submission.zip")
    print("wrote", OUT / "submission.json", "and", OUT / "submission.zip")
