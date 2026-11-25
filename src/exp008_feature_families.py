"""Experiment 008: engineered feature families, one at a time, on top of each task's champion features.

Usage: python src/exp008_feature_families.py          # all families × both tasks, cv_seed 2026
       python src/exp008_feature_families.py confirm  # re-test the BETTER / NEAR-MISS ones on cv_seeds 2027, 2028

Families (TODO.md #1–#5). All are row-wise ratios the trees cannot build themselves:
  reltiming  std_iat/mean_iat, max_iat/mean_iat, (max_iat-min_iat)/mean_iat
  rates      bytes_up/duration, bytes_down/duration   (packets/s ≈ 1/mean_iat, so left out)
  burst      burst_count/duration, packets per burst, bytes per burst
  direction  downstream share of bytes and of packets
  sizecv     std_pkt_size/mean_pkt_size per direction
Timing-based families are computed from the raw columns, so on task 2 they re-add timing information
in ratio form (the champion has no raw timing columns).
"""
import json
import sys
from datetime import datetime, timezone

import numpy as np

from cv import TASK_FEATURES, TASKS, evaluate
from models import SoftVote
from runlog import RESULTS, load_index, record_run


def softvote(seed):
    return SoftVote(seed=seed)


def div(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return np.where(b > 0, a / np.where(b > 0, b, 1), 0.0)


def reltiming(R):
    return {"cv_iat": div(R.std_iat, R.mean_iat), "max_over_mean_iat": div(R.max_iat, R.mean_iat),
            "range_over_mean_iat": div(R.max_iat - R.min_iat, R.mean_iat)}


def rates(R):
    return {"bytes_up_per_s": div(R.bytes_up, R.duration), "bytes_down_per_s": div(R.bytes_down, R.duration)}


def burst(R):
    n = R.packet_count_up + R.packet_count_down
    return {"bursts_per_s": div(R.burst_count, R.duration), "pkts_per_burst": div(n, R.burst_count),
            "bytes_per_burst": div(R.bytes_up + R.bytes_down, R.burst_count)}


def direction(R):
    return {"down_byte_share": div(R.bytes_down, R.bytes_up + R.bytes_down),
            "down_pkt_share": div(R.packet_count_down, R.packet_count_up + R.packet_count_down)}


def sizecv(R):
    return {"cv_size_up": div(R.std_pkt_size_up, R.mean_pkt_size_up),
            "cv_size_down": div(R.std_pkt_size_down, R.mean_pkt_size_down)}


FAMILIES = {f.__name__: f for f in (reltiming, rates, burst, direction, sizecv)}


def with_families(task, names):
    base = TASK_FEATURES[task]

    def feats(X_raw):
        X = base(X_raw)
        for n in names:
            for col, v in FAMILIES[n](X_raw).items():
                X[col] = v
        return X
    feats.__name__ = f"{base.__name__}+{'+'.join(names)}"
    return feats


def run(task, names, cv_seed=2026, reference="champion", tag=""):
    f = with_families(task, names)
    t0 = datetime.now(timezone.utc)
    res = {task: evaluate(task, f, softvote, cv_seed=cv_seed)}
    short = "t1" if task == TASKS[0] else "t2"
    return record_run("008", f"{short}_{'+'.join(names)}{tag}", res, reference=reference,
                      question=f"Does adding {', '.join(names)} to the {short} champion help (cv_seed {cv_seed})?",
                      model_factory=softvote, feature_fn=f,
                      config={"model": "SoftVote", "features": f.__name__, "cv_seed": cv_seed}, started=t0)


def main():
    for task in TASKS:
        for name in FAMILIES:
            run(task, [name])


def confirm():
    """Re-test every 008 single-family run that was BETTER or NEAR-MISS on fresh folds."""
    todo = [(t, e["name"]) for e in load_index() if e["experiment"] == "008" and "_s20" not in e["name"]
            for t, v in e["verdicts"].items() if v.get("verdict") in ("BETTER", "NEAR-MISS (inconclusive)")]
    for seed in (2027, 2028):
        for task in sorted({t for t, _ in todo}):
            base = TASK_FEATURES[task]
            t0 = datetime.now(timezone.utc)
            ref = record_run("008", f"{'t1' if task == TASKS[0] else 't2'}_champion_s{seed}",
                             {task: evaluate(task, base, softvote, cv_seed=seed)}, reference=None,
                             question=f"Confirmation reference: champion features, cv_seed {seed}.",
                             model_factory=softvote, feature_fn=base,
                             config={"model": "SoftVote", "features": base.__name__, "cv_seed": seed}, started=t0)
            for t, name in todo:
                if t == task:
                    run(task, name.split("_", 1)[1].split("+"), cv_seed=seed, reference=ref, tag=f"_s{seed}")


if __name__ == "__main__":
    confirm() if sys.argv[1:] == ["confirm"] else main()
