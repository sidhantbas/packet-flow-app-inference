#!/bin/bash
# Start a new capture group and run a session plan in one terminal (experiment 054 follow-up; Charles's handoff, sections 4-7).
#   bash src/capture_group.sh long cellular     new group, long plan (idle, 20 min Facebook/Instagram/YouTube, idle)
# Creates data/captures/raw/sid-iphone-<UTC>-<plan>-<network>/ with setup.txt and an environment.md to fill in,
# waits for the phone, starts its RVI, runs src/capture_pilot.sh with that plan, then stops the RVI.
# Raw files stay in the gitignored data/captures/raw/. No address is printed by this script.
set -u
cd "$(dirname "$0")/.." || exit 1
umask 077
PLAN=${1:-long}
NET=${2:-cellular}
UDID=${SID_PHONE_UDID:-00008150-00181D391484401C}
RVICTL=/Library/Apple/usr/bin/rvictl

clear
cat <<TXT
=== New capture group: plan "$PLAN", network "$NET" ===

Prepare the PHONE (each step matters for the data):
  1. Settings > Wi-Fi: OFF.  Settings > Cellular > Cellular Data: ON.
     (Our home Wi-Fi blocks QUIC for Instagram/YouTube, experiment 052.)
  2. Settings > Cellular > Cellular Data Options > Data Mode: Standard (NOT Low Data Mode).
  3. Settings > Display & Brightness > Auto-Lock: Never (the screen must stay on for 20 minutes).
  4. VPN off, iCloud Private Relay off (as in the pilot).
  5. Close Facebook, Instagram and YouTube (swipe them away in the app switcher), so each starts fresh.
  6. Plug the phone into this Mac with the USB data cable and unlock it. Tap Trust if asked.

Data use: about 0.7-1 GB per 20-minute app session on cellular (about 3 GB in total).
At each session prompt you can type s to skip it (for example YouTube, to save data).
Total time: about 65 minutes. Keep this window open; do not close the lid of the Mac.
TXT
read -r -p "Press Enter when steps 1-6 are done... " _

until xcrun devicectl list devices 2>/dev/null | grep "$UDID" | grep -q connected; do
  read -r -p "Phone not seen yet. Unlock it, tap Trust if asked, then press Enter... " _
done

ROOT="$PWD/data/captures/raw/sid-iphone-$(date -u +%Y%m%dT%H%M%SZ)-$PLAN-$NET"
mkdir -p "$ROOT" || exit 1
printf '%s\n' "$ROOT" > data/captures/raw/latest-sid-capture-root.txt
{ date -u +%FT%TZ; sw_vers; xcodebuild -version; xcode-select -p; /usr/sbin/tcpdump --version; git rev-parse HEAD; df -h .; } > "$ROOT/setup.txt" 2>&1
cat > "$ROOT/environment.md" <<ENV
# Environment: $(basename "$ROOT")

- Mac: $(sysctl -n hw.model), macOS $(sw_vers -productVersion), $(xcodebuild -version | head -1), \`/usr/sbin/tcpdump\`.
- iPhone: iPhone 17 Pro ("SidPhone"), USB data cable, Trust approved.
- Plan: $PLAN. Network: $NET (Wi-Fi off). Data Mode: FILL IN (Standard / Low Data). Auto-Lock: FILL IN.
- iOS version: FILL IN · Facebook: FILL IN · Instagram: FILL IN · YouTube: FILL IN
- VPN: FILL IN · iCloud Private Relay: FILL IN · Signal (bars, 4G/5G): FILL IN
- Apps closed before their session: FILL IN · Logged in to all apps: FILL IN
- What you did in each app (feed, Reels, Stories, videos, pauses): FILL IN
- Anything unusual (calls, notifications, buffering, app updates, settings changed): FILL IN
ENV
echo
echo "Group folder: $ROOT"
echo "Starting RVI..."
"$RVICTL" -s "$UDID" | tee "$ROOT/rvi-start.txt"
if ! ifconfig rvi0 >/dev/null 2>&1; then
  echo "rvi0 did not come up. If you see bootstrap_look_up 1102, run:"
  echo "  sudo launchctl load -w /Library/Apple/System/Library/LaunchDaemons/com.apple.rpmuxd.plist"
  echo "then run this script again. Copy this window's text to Claude."
  exit 1
fi
ifconfig rvi0 > "$ROOT/rvi-interface-details.txt"

PLAN="$PLAN" bash src/capture_pilot.sh
status=$?

echo
"$RVICTL" -x "$UDID" | tee "$ROOT/rvi-stop.txt"
"$RVICTL" -l > "$ROOT/rvi-devices-after-stop.txt" 2>&1
echo
if [ $status -eq 0 ]; then
  echo "All done. Turn Wi-Fi back on and Auto-Lock back to your usual setting."
  echo "Then fill in the FILL IN lines of: $ROOT/environment.md (or paste the answers to Claude)."
  echo "Tell Claude: 'long group done'."
else
  echo "The run stopped early (status $status). Do not start another recording. Copy this window's text to Claude."
fi
