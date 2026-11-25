"""Experiment 122, part 3: arithmetic checks of the capture-to-feature definitions (Charles's 20 October handoff, deliverable 3).

Command: .venv/bin/python src/exp122_definition_checks.py
Runs the same identities on the organisers' released feature rows (train + validation + test features of both tasks; no labels)
and on our clean extraction (data/captures/clean-v2/, all rows), so each definition in
docs/captures/capture-to-features-definitions.md carries a measured status for both sides. Writes
experiments/122_evidence/definition_checks.json.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OFFICIAL = ROOT / "data/official/dataset"
CLEAN = ROOT / "data/captures/clean-v2"
OUT = ROOT / "experiments/122_evidence"


def load_official(task):
    return pd.concat([pd.read_csv(OFFICIAL / task / f"{s}_features.csv") for s in ("train", "validation", "test")], ignore_index=True)


def load_clean(task):
    parts = [pd.read_csv(p).assign(group=p.parent.parent.name) for p in sorted(CLEAN.glob(f"*/*/{task}_features.csv"))]
    return pd.concat([d for d in parts if len(d)], ignore_index=True)


def checks(T1, T2):
    n1 = T1.packet_count_up + T1.packet_count_down
    n2 = T2.packet_count_up + T2.packet_count_down
    frac = lambda m: round(float(np.mean(m)), 4)
    has_up, has_dn = T1.packet_count_up > 0, T1.packet_count_down > 0
    gap_ok = n1 > 1
    return {
        "flows": len(T1),
        "min_packets_task1": int(n1.min()),
        "task2_exactly_5_packets": frac(n2 == 5),
        "duration_eq_mean_iat_x_gaps": frac(np.isclose(T1.duration[gap_ok], T1.mean_iat[gap_ok] * (n1[gap_ok] - 1), rtol=1e-6, atol=1e-6)),
        "bytes_eq_count_x_mean_up": frac(np.isclose(T1.bytes_up[has_up], T1.packet_count_up[has_up] * T1.mean_pkt_size_up[has_up], atol=1e-3)),
        "bytes_eq_count_x_mean_down": frac(np.isclose(T1.bytes_down[has_dn], T1.packet_count_down[has_dn] * T1.mean_pkt_size_down[has_dn], atol=1e-3)),
        "integer_bytes": frac((T1.bytes_up % 1 == 0) & (T1.bytes_down % 1 == 0)),
        "min_frame_ge_60": frac(((T1.mean_pkt_size_down >= 60) | ~has_dn) & ((T1.mean_pkt_size_up >= 60) | ~has_up)),
        "max_mean_frame": float(max(T1.mean_pkt_size_up.max(), T1.mean_pkt_size_down.max())),
        "packet_ratio_eq_up_over_max_down_1": frac(np.isclose(T1.up_down_packet_ratio, T1.packet_count_up / T1.packet_count_down.clip(lower=1))),
        "byte_ratio_eq_up_over_max_down_1": frac(np.isclose(T1.up_down_byte_ratio, T1.bytes_up / T1.bytes_down.clip(lower=1))),
        "burst_1_when_max_iat_lt_1s": frac(T1.burst_count[T1.max_iat < 1.0] == 1),
        "burst_ge2_when_max_iat_ge_1s": frac(T1.burst_count[T1.max_iat >= 1.0] >= 2),
        "duration_on_1us_grid": frac(np.isclose(T1.duration * 1e6, np.round(T1.duration * 1e6), atol=1e-3)),
        "min_iat_zero_task1": frac(T1.min_iat == 0),
        "min_iat_zero_task2": frac(T2.min_iat == 0),
        "prefix_le_full_counts": frac((T2.packet_count_up <= T1.packet_count_up) & (T2.packet_count_down <= T1.packet_count_down)),
        "prefix_duration_le_full": frac(T2.duration <= T1.duration + 1e-9),
        "max_iat_le_duration": frac(T1.max_iat <= T1.duration + 1e-9),
        "std_zero_when_le_1_packet_up": frac(T1.std_pkt_size_up[T1.packet_count_up <= 1] == 0),
        "transport_tcp_share": frac(T1.transport == "tcp"),
        "server_ports": {str(k): int(v) for k, v in T1.server_port.value_counts().items()},
        "task2_tcp_opening_shapes_up_down": {f"{u}/{d}": int(c) for (u, d), c in
                                             T2[T2.transport == "tcp"].groupby(["packet_count_up", "packet_count_down"]).size()
                                             .sort_values(ascending=False).head(5).items()},
    }


def main():
    O1, O2 = load_official("task1_static"), load_official("task2_realtime_prefix5")
    assert (O1.flow_id == O2.flow_id).all()
    C1, C2 = load_clean("task1"), load_clean("task2")
    assert (C1.flow_id == C2.flow_id).all()
    res = {"experiment": "122", "organisers_all_released_rows": checks(O1, O2), "ours_clean_v2_all_rows": checks(C1, C2),
           "ours_by_group": {g: checks(C1[C1.group == g], C2[C2.group == g]) for g in sorted(C1.group.unique())}}
    OUT.mkdir(exist_ok=True)
    (OUT / "definition_checks.json").write_text(json.dumps(res, indent=2) + "\n")
    a, b = res["organisers_all_released_rows"], res["ours_clean_v2_all_rows"]
    for k in a:
        print(f"{k:38s} organisers {str(a[k])[:60]:60s} ours {str(b[k])[:60]}")


if __name__ == "__main__":
    main()
