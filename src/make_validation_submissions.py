"""Build Validation Phase submission files (train-only models) and score them locally with the official evaluate().

Command: .venv/bin/python src/make_validation_submissions.py
For each model below: fit on the TRAIN split only, predict the VALIDATION split, write
submissions/validation-phase/<name>/submission.json and .zip, and score them with the unchanged official
data/official/evaluation_script/main.py against the public validation labels. The Validation Phase does not count for the
ranking; these scores are a pipeline check and a single-split view, never used to choose models (selection = 50-fold CV).
"""
import json
import tempfile
from pathlib import Path

import pandas as pd

import make_submission as m
from cv import TASK_FEATURES, TASKS, basic_features, load_task, task1_prefix_rest_features
from exp005_checks import official_module
from models import SoftVote, TASK_MODELS, task1_model

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "submissions" / "validation-phase"


def t1_models():
    import exp062_task1_nonmeta_thresholds as e62
    import exp065_task1_rest_expert as e65
    import exp075_rest_expert_plus_nonmeta_thresholds as e75
    import exp077_fingerprint_expert as e77
    return {
        "production-034": (TASK_MODELS["task1_static"], TASK_FEATURES["task1_static"]),
        "022-whole-flow-blend (84.62 file's model)": (task1_model, TASK_FEATURES["task1_static"]),
        "004-softvote (83.56 file's model)": (lambda s: SoftVote(seed=s), basic_features),
        "065-rest-expert (066 file)": (e65.make_factory("R"), task1_prefix_rest_features),
        "077-fingerprint-rest": (e77.make_factory("FR"), e77.features),
        "062-nonmeta-thresholds": (e62.nonmeta_model, TASK_FEATURES["task1_static"]),
        "075-rest-plus-thresholds": (e75.combo_model, task1_prefix_rest_features),
    }


def fit_predict_val(task, factory, feats):
    Xtr, ytr = load_task(task, ("train",))
    Xva, _ = load_task(task, ("validation",))
    model = factory(0).fit(feats(Xtr), ytr)
    return dict(zip(Xva.flow_id, [str(p) for p in model.predict(feats(Xva))]))


def main():
    evaluate = official_module().evaluate
    truth = {t: dict(zip(*[load_task(t, ("validation",))[0].flow_id, load_task(t, ("validation",))[1]])) for t in TASKS}
    p2 = fit_predict_val("task2_realtime_prefix5", TASK_MODELS["task2_realtime_prefix5"], TASK_FEATURES["task2_realtime_prefix5"])
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        ann = Path(tmp) / "annotations.json"
        ann.write_text(json.dumps({"tasks": truth}))
        for name, (factory, feats) in t1_models().items():
            p1 = fit_predict_val("task1_static", factory, feats)
            for t, p in (("task1_static", p1), ("task2_realtime_prefix5", p2)):
                m.check(p, t, split="validation")
            d = OUT / name.split(" ")[0]
            d.mkdir(parents=True, exist_ok=True)
            m.write_submission({"task1_static": p1, "task2_realtime_prefix5": p2}, d / "submission.json", d / "submission.zip")
            res = evaluate(str(ann), str(d / "submission.zip"), "dev")["submission_result"]
            res_json = evaluate(str(ann), str(d / "submission.json"), "dev")["submission_result"]
            assert res == res_json
            rows.append({"folder": d.name, "model": name, **{k: round(v, 4) for k, v in res.items()}})
            print(f"{name:45s} " + "  ".join(f"{k} {v:.4f}" for k, v in res.items()))
    T = pd.DataFrame(rows)
    T.to_csv(OUT / "local_official_scores.csv", index=False)
    (OUT / "README.md").write_text(
        "# Validation Phase files (train-only models)\n\nEach folder holds `submission.json` and `submission.zip` for the Validation Phase: Task 1 from the "
        "named model, Task 2 from production (014); every model fitted on the train split only. Scores below come from the unchanged official "
        "`evaluate()` run locally against the public validation labels; the platform should show the same numbers. **Pipeline check and "
        "single-split view only: the Validation Phase does not count for the ranking, and models are never chosen by these scores "
        "(selection = 50-fold CV).**\n\n" + T.to_markdown(index=False) + "\n")


if __name__ == "__main__":
    main()
