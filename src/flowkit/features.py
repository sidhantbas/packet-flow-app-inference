"""Derived flow features. Inputs use the basic column names (cv.basic_features) of either task, or a prefix such as "p5_"."""
import numpy as np
import pandas as pd


def _div(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return np.where(b > 0, a / np.where(b > 0, b, 1.0), 0.0)


def ratio_features(X, prefix=""):
    """Ratio, rate and coefficient-of-variation features (as named in experiment 103's reading of LLM_ops's note)."""
    c = lambda name: X[prefix + name]  # noqa: E731
    out = {
        "cv_size_up": _div(c("std_pkt_size_up"), c("mean_pkt_size_up")),
        "cv_size_down": _div(c("std_pkt_size_down"), c("mean_pkt_size_down")),
        "bytes_per_s_up": _div(c("bytes_up"), c("duration")),
        "bytes_per_s_down": _div(c("bytes_down"), c("duration")),
        "packets_per_s": _div(c("packet_count_up") + c("packet_count_down"), c("duration")),
        "iat_cv": _div(c("std_iat"), c("mean_iat")),
        "bursts_per_s": _div(c("burst_count"), c("duration")),
    }
    return pd.DataFrame({prefix + k: v for k, v in out.items()}, index=X.index)
