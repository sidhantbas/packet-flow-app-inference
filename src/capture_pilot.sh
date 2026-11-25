#!/bin/bash
# iPhone capture pilot in one terminal (Charles's handoff, data/charles/docs/sid-iphone-capture-handoff.md, sections 6-7).
# For each session: start tcpdump on the RVI, wait for "listening", log action-start, count down, log action-end,
# stop tcpdump with SIGINT (same as Ctrl-C) by its exact PID, then hash, read back and ask for a note.
#
#   bash src/capture_pilot.sh                     all 7 sessions; sessions already recorded are skipped
#   bash src/capture_pilot.sh 03-facebook-reels   one session; a suffixed name (03-facebook-reels-retry, 04-instagram-feed-cellular) keeps the action
#   PLAN=long bash src/capture_pilot.sh           long-session plan (054): idle, 20 min each of Facebook, Instagram, YouTube, idle
#   PLAN=check SID_RVI=bridge100 bash src/capture_pilot.sh   059 signature check: 5 min Facebook, 5 min Instagram
#
# Needs: the RVI running (rvictl -s <UDID>) and a capture group in data/captures/raw/latest-sid-capture-root.txt.
# DUR (default 60) sets pilot session length, LONG_DUR (default 1200) the long-plan app sessions, GAP (default 30) the pause.
# At each "press Enter" prompt, typing s skips that session (logged).
set -u
set -m  # job control: background jobs get normal SIGINT handling (a script otherwise starts them with SIGINT ignored)
cd "$(dirname "$0")/.." || exit 1
umask 077

RVI=${SID_RVI:-rvi0}
DUR=${DUR:-60}
LONG_DUR=${LONG_DUR:-1200}
CHECK_DUR=${CHECK_DUR:-300}
GAP=${GAP:-30}
PLAN=${PLAN:-pilot}
SUDO=${SUDO-sudo}
SUDON=${SUDO:+$SUDO -n}  # never prompt in the background: fail instead of hanging
TCPDUMP=${TCPDUMP:-/usr/sbin/tcpdump}

# name|seconds|action
PILOT=(
  "01-idle|$DUR|Leave the phone on the home screen. Do not touch it."
  "02-facebook-feed|$DUR|Open Facebook, pull to refresh once, scroll at a normal pace."
  "03-facebook-reels|$DUR|Open Facebook Reels, pick fresh Reels now, watch or swipe normally."
  "04-instagram-feed|$DUR|Open Instagram, pull to refresh once, scroll at a normal pace."
  "05-instagram-reels|$DUR|Open Instagram Reels, pick fresh Reels now, watch or swipe normally."
  "06-youtube-video|$DUR|Open YouTube, pick a fresh video now, play it continuously."
  "07-idle-after|$DUR|Go back to the home screen. Do not touch the phone."
)
LONG=(  # 054: training Meta flows last 205-235 s at the median; 049: Meta sessions need >= 20 min
  "01-idle|60|Leave the phone on the home screen. Do not touch it."
  "02-facebook|$LONG_DUR|Open Facebook and use it normally until STOP: feed, Reels, videos, open some posts and comments. Pausing on a post is fine. Stay in Facebook; keep the screen on."
  "03-instagram|$LONG_DUR|Open Instagram and use it normally until STOP: feed, Reels, Stories, open some posts. Pausing on a post is fine. Stay in Instagram; keep the screen on."
  "04-youtube|$LONG_DUR|Open YouTube and use it normally until STOP: pick fresh videos, Shorts, browse Home. Stay in YouTube; keep the screen on."
  "05-idle-after|60|Go back to the home screen. Do not touch the phone."
)
CHECK=(  # 059: Android signature check
  "01-facebook|$CHECK_DUR|Open Facebook and use it normally until STOP: feed, Reels, videos. Stay in Facebook; keep the screen on."
  "02-instagram|$CHECK_DUR|Open Instagram and use it normally until STOP: feed, Reels, Stories. Stay in Instagram; keep the screen on."
)
case "$PLAN" in
  pilot) SESSIONS=("${PILOT[@]}") ;;
  long) SESSIONS=("${LONG[@]}") ;;
  check) SESSIONS=("${CHECK[@]}") ;;
  *) echo "PLAN must be pilot, long or check"; exit 1 ;;
esac

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
beep() { afplay /System/Library/Sounds/Glass.aiff >/dev/null 2>&1 & }
running() { ps -p "$1" >/dev/null 2>&1; }

ROOT=${SID_CAPTURE_ROOT:-$(cat data/captures/raw/latest-sid-capture-root.txt 2>/dev/null)}
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "No capture group found (data/captures/raw/latest-sid-capture-root.txt)."; exit 1; }
LOG="$ROOT/pilot-log.tsv"
log() { printf '%s\t%s\n' "$(now)" "$*" >> "$LOG"; }

if [ -z "${TCPDUMP_TEST:-}" ] && ! ifconfig "$RVI" >/dev/null 2>&1; then
  echo "$RVI is not up. iPhone: start it with /Library/Apple/usr/bin/rvictl -s <UDID>; Android: turn on Internet Sharing (bridge100)."
  exit 1
fi

countdown() {  # seconds, label
  local end=$(( $(date +%s) + $1 )) left
  while :; do
    left=$(( end - $(date +%s) ))
    [ "$left" -le 0 ] && break
    printf '\r   %s: %3d s left ' "$2" "$left"
    sleep 1
  done
  printf '\r   %s: done.          \n' "$2"
}

record() {  # name, seconds, action
  local name=$1 dur=$2 action=$3 D="$ROOT/$1" bg pid i ans
  if [ -e "$D" ]; then echo "== $name already exists, skipped."; return 0; fi
  echo
  echo "== $name"
  echo "   Length: $((dur / 60)) min $((dur % 60)) s"
  echo "   Action: $action"
  printf '   Unlock the phone, then press Enter to start recording (or type s and Enter to skip): '
  read -r ans
  if [ "$ans" = "s" ]; then echo "   Skipped."; log "$name: skipped by the user"; return 0; fi
  mkdir "$D" || return 1
  log "$name: recorder start requested"
  now > "$D/capture-start-request.txt"
  # sh prints its PID and then execs tcpdump, so that PID is tcpdump's own: no guessing, no killall.
  $SUDON sh -c 'echo "PID $$" >&2; exec "$0" "$@"' "$TCPDUMP" -i "$RVI" -nn -p -P -s 0 -w - 'ip or ip6' \
    > "$D/packets.pcapng" 2> "$D/capture.log" &
  bg=$!
  for i in $(seq 1 40); do
    grep -q 'listening on' "$D/capture.log" 2>/dev/null && break
    running "$bg" || break
    sleep 0.25
  done
  if ! grep -q 'listening on' "$D/capture.log" 2>/dev/null; then
    echo "   Recorder did not start. Log:"; cat "$D/capture.log"
    log "$name: FAILED, recorder did not start"
    return 1
  fi
  pid=$(sed -n 's/^PID //p' "$D/capture.log" | head -1)
  echo "   Recording ($(grep 'listening on' "$D/capture.log"))"
  beep
  printf '%s\t%s\n' "$(now)" "action-start: $action" >> "$D/actions.tsv"
  echo "   >>> GO: do the action now."
  countdown "$dur" "$name"
  printf '%s\t%s\n' "$(now)" "action-end: $dur s timer finished" >> "$D/actions.tsv"
  beep
  echo "   <<< STOP: put the phone down."
  $SUDON kill -INT "$pid"
  for i in $(seq 1 60); do running "$bg" || break; sleep 0.25; done
  if running "$bg"; then
    echo "   !!! The recorder (PID $pid) did not stop. Do NOT start another recording. Tell Claude."
    log "$name: FAILED, recorder PID $pid did not stop after SIGINT"
    exit 2
  fi
  wait "$bg" 2>/dev/null
  now > "$D/capture-finished.txt"
  log "$name: recorder stopped"
  chmod 600 "$D/packets.pcapng"
  shasum -a 256 "$D/packets.pcapng" > "$D/packets.sha256"
  wc -c < "$D/packets.pcapng" > "$D/packet-file-bytes.txt"
  "$TCPDUMP" -nn -c 10 -r "$D/packets.pcapng" > "$D/header-sample.txt" 2> "$D/readback.log"
  "$TCPDUMP" -nn -tt -k IDNd -c 10 -r "$D/packets.pcapng" > "$D/metadata-sample.txt" 2> "$D/metadata-readback.log"
  echo "   $(grep 'packets captured' "$D/capture.log") / $(grep 'dropped by kernel' "$D/capture.log")"
  if grep -q -i -E 'truncated|malformed|error|bad' "$D/readback.log"; then
    echo "   !!! Readback problem:"; cat "$D/readback.log"
    log "$name: readback problem"
  else
    echo "   Readback OK."
  fi
  printf '   Note (app already open? ads, buffering, interruptions; Enter for none): '
  read -r note
  printf '%s\t%s\n' "$(now)" "note: ${note:-none}" >> "$D/actions.tsv"
  log "$name: done"
}

if [ -z "${TCPDUMP_TEST:-}" ]; then
  echo "Password for sudo (asked once; kept fresh during the pilot):"
  $SUDO -v || exit 1
  ( while :; do $SUDO -n true 2>/dev/null; sleep 50; done ) &
  KEEP=$!
  trap 'kill $KEEP 2>/dev/null' EXIT
fi

echo "Capture group: $ROOT"
echo "Plan: $PLAN. A ${GAP} s pause between sessions. A sound plays at GO and at STOP."
log "run started (PLAN=$PLAN DUR=$DUR LONG_DUR=$LONG_DUR GAP=$GAP)"

if [ $# -gt 0 ]; then
  dur=$DUR action="Describe the action in the note."
  for s in "${SESSIONS[@]}"; do case "$1" in "${s%%|*}"*) r=${s#*|}; dur=${r%%|*}; action=${r#*|} ;; esac; done  # e.g. 04-instagram-feed-cellular
  record "$1" "$dur" "$action"
  exit $?
fi

first=1
for s in "${SESSIONS[@]}"; do
  name=${s%%|*}
  [ -e "$ROOT/$name" ] && { echo "== $name already exists, skipped."; continue; }
  if [ $first -eq 0 ]; then log "gap before $name"; countdown "$GAP" "pause"; fi
  r=${s#*|}
  record "$name" "${r%%|*}" "${r#*|}" || { echo "Stopped at $name."; exit 1; }
  first=0
done

echo
echo "Run done. Sessions in $ROOT:"
for s in "${SESSIONS[@]}"; do
  name=${s%%|*}
  [ -f "$ROOT/$name/capture.log" ] && printf '   %-20s %s\n' "$name" "$(grep 'packets captured' "$ROOT/$name/capture.log")"
done
echo "Next: tell Claude the run is done."
