"""Experiment 021: the Facebook validation gap.

Diagnostic (see experiments/021_facebook_tcp.md): trained on train only, Facebook F1 on validation is 0.00 (task 1).
7 of 8 train Facebook flows are UDP; all 3 validation Facebook flows are long-lived TCP with tiny download packets
and more upload than download bytes (a Meta keep-alive-like signature, shared by the one Instagram TCP flow).
In 50-split CV on train+validation the champion already catches the long TCP ones.

Variant (both tasks, on the champion): explicit TCP-conditioned signature features, since trees need several
splits to express "TCP and small download packets and up > down":
  tcp_down_pkt   mean_pkt_size_down if TCP else -1
  tcp_ratio      up_down_byte_ratio if TCP else -1
  down_share     bytes_down / (bytes_up + bytes_down)
"""
from datetime import datetime, timezone

import numpy as np

from cv import TASK_FEATURES, TASKS, evaluate
from models import TASK_MODELS
from runlog import record_run


def meta_sig(task):
    base = TASK_FEATURES[task]

    def f(X_raw):
        X = base(X_raw)
        tcp = (X_raw.transport == "tcp").values
        X["tcp_down_pkt"] = np.where(tcp, X_raw.mean_pkt_size_down, -1.0)
        X["tcp_ratio"] = np.where(tcp, X_raw.up_down_byte_ratio, -1.0)
        total = (X_raw.bytes_up + X_raw.bytes_down).values
        X["down_share"] = np.where(total > 0, X_raw.bytes_down / np.where(total > 0, total, 1), 0.0)
        return X
    f.__name__ = f"{base.__name__}+meta_sig"
    return f


if __name__ == "__main__":
    t0 = datetime.now(timezone.utc)
    res = {t: evaluate(t, meta_sig(t), TASK_MODELS[t]) for t in TASKS}
    record_run("021", "meta_sig", res, model_factory=TASK_MODELS[TASKS[0]],
               question="Do TCP-conditioned Meta-signature features help (Facebook especially)?",
               config={"model": "TASK_MODELS", "features": "champion + tcp_down_pkt, tcp_ratio, down_share"}, started=t0)
