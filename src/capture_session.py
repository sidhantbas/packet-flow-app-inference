"""Log one capture session with exact UTC times (experiment 042). Run in a second terminal while tcpdump records.

Command: .venv/bin/python src/capture_session.py <app> <activity> <minutes>
  e.g.   .venv/bin/python src/capture_session.py facebook idle-feed 20
Writes start and end (UTC, from this Mac's clock, the same clock as tcpdump) to data/captures/sessions.csv.
Ctrl-C ends the session early and still records the real end time. After each session it counts down the 2-minute gap.
"""
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

APPS = {"baseline", "facebook", "instagram", "google", "youtube", "mozilla", "x"}
FILE = Path(__file__).resolve().parent.parent / "data" / "captures" / "sessions.csv"
GAP = 120


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def countdown(seconds, label):
    end = time.time() + seconds
    while (left := end - time.time()) > 0:
        print(f"\r  {label}: {int(left) // 60:02d}:{int(left) % 60:02d} left ", end="", flush=True)
        time.sleep(1)
    print()


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in APPS:
        sys.exit(__doc__ + f"\napps: {sorted(APPS)}")
    app, activity, minutes = sys.argv[1], sys.argv[2], float(sys.argv[3])
    FILE.parent.mkdir(parents=True, exist_ok=True)
    new = not FILE.exists()
    n = 0 if new else sum(1 for _ in open(FILE)) - 1
    sid = f"{datetime.now(timezone.utc):%Y%m%d}-{n + 1:02d}"
    start = now()
    print(f"session {sid}: {app} / {activity}, started {start}. Only {app} open; Ctrl-C to stop early.")
    try:
        countdown(minutes * 60, f"{app} {activity}")
    except KeyboardInterrupt:
        print("\n  stopped early")
    end = now()
    with open(FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["session_id", "app", "activity", "start_utc", "end_utc"])
        w.writerow([sid, app, activity, start, end])
    print(f"logged {sid} ({start} -> {end}) in {FILE}")
    print("Now: swipe the app away in the app switcher, go to the home screen, and leave the phone alone.")
    try:
        countdown(GAP, "gap before the next session")
    except KeyboardInterrupt:
        print("\n  gap cut short")


if __name__ == "__main__":
    main()
