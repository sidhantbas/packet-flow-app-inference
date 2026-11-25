"""Phase 4b: feature-gap hypotheses derivable from existing columns, tested on top of production (PROTOCOL.md H1-H5)."""
import math

import numpy as np
import pandas as pd

from common import T1, T2, TASK_FEATURES, paired, run, save
from models import rest_from_columns

ACK = 66


def _int(v):
    return abs(v - round(v)) <= 0.01


def _decode(n, m, s):
    n = int(n)
    if n == 1:
        return [round(m)] if _int(m) else None
    if n == 2:
        a, b = m - s, m + s
        return sorted([round(a), round(b)]) if _int(a) and _int(b) else None
    if n > 2 and abs(s) < 1e-9:
        return [round(m)] * n if _int(m) else None
    return None


def _tcp3(m, s):
    S, Q = 3 * m, 3 * (s ** 2 + m ** 2)
    a, b = S - ACK, Q - ACK ** 2
    disc = 2 * b - a ** 2
    if disc < -1e-6:
        return None
    r = math.sqrt(max(disc, 0.0))
    x, y = (a - r) / 2, (a + r) / 2
    return (round(x), round(y)) if _int(x) and _int(y) and 140 <= round(x) <= 180 else None


def stamps(X, p=""):
    """090 stamps from the opening columns (prefix p: 'p5_' in Task 1, '' in Task 2); transport is 1 for UDP."""
    rows = []
    for _, r in X.iterrows():
        tcp = r[f"{p}transport"] == 0
        up = _decode(r[f"{p}packet_count_up"], r[f"{p}mean_pkt_size_up"], r[f"{p}std_pkt_size_up"])
        dn = _decode(r[f"{p}packet_count_down"], r[f"{p}mean_pkt_size_down"], r[f"{p}std_pkt_size_down"])
        syn = hello = synack = reply = -1
        if tcp and up is None and int(r[f"{p}packet_count_up"]) == 3:
            d = _tcp3(r[f"{p}mean_pkt_size_up"], r[f"{p}std_pkt_size_up"])
            if d:
                syn, hello = d
                up = sorted([ACK, *d])
        if tcp and dn:
            synack = dn[0]
            reply = dn[1] if len(dn) == 2 else -1
        rows.append({"st_syn": syn, "st_hello": hello, "st_synack": synack, "st_reply": reply,
                     "st_up_min": min(up) if up else -1, "st_up_max": max(up) if up else -1,
                     "st_down_min": min(dn) if dn else -1, "st_down_max": max(dn) if dn else -1})
    return pd.DataFrame(rows, index=X.index)


def safe(a, b):
    return np.where(np.asarray(b, float) > 0, np.asarray(a, float) / np.where(np.asarray(b, float) > 0, np.asarray(b, float), 1), 0.0)


def h1(X, task):
    return stamps(X, "p5_" if task == T1 else "")


def h2(X, task):
    R = rest_from_columns(X)
    return pd.DataFrame({"h2_tempo_ratio": safe(R.r_mean_iat, np.maximum(X.p5_mean_iat, 1e-3)),
                         "h2_down_size_ratio": safe(R.r_mean_size_down, X.p5_mean_pkt_size_down)}, index=X.index)


def h3(X, task):
    n = X.packet_count_up + X.packet_count_down
    b = X.bytes_up + X.bytes_down
    return pd.DataFrame({"h3_pkts_per_burst": safe(n, X.burst_count), "h3_bytes_per_burst": safe(b, X.burst_count)}, index=X.index)


def h4(X, task):
    return pd.DataFrame({"h4_size_asym": X.mean_pkt_size_up - X.mean_pkt_size_down,
                         "h4_cv_up": safe(X.std_pkt_size_up, X.mean_pkt_size_up),
                         "h4_cv_down": safe(X.std_pkt_size_down, X.mean_pkt_size_down)}, index=X.index)


def h5(X, task):
    return pd.DataFrame({"h5_open_byte_share": safe(X.p5_bytes_up + X.p5_bytes_down, X.bytes_up + X.bytes_down),
                         "h5_open_time_share": safe(X.p5_duration, X.duration)}, index=X.index)


HYP = {"H1": (h1, (T1, T2)), "H2": (h2, (T1,)), "H3": (h3, (T1, T2)), "H4": (h4, (T1, T2)), "H5": (h5, (T1,))}


def with_extra(task, h):
    base = TASK_FEATURES[task]

    def f(X):
        B = base(X).reset_index(drop=True)
        return pd.concat([B, h(B, task)], axis=1)
    f.__name__ = f"{base.__name__}_plus_{h.__name__}"
    f.extra_data = getattr(base, "extra_data", [])
    return f


def main():
    out = {}
    for hid, (h, tasks) in HYP.items():
        for task in tasks:
            out[f"{hid}:{task}"] = paired(task, run(task, features=with_extra(task, h)))
            print(hid, task, out[f"{hid}:{task}"], flush=True)
    save("phase4b_hypotheses.json", out)


if __name__ == "__main__":
    main()
