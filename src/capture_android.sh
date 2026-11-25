#!/bin/bash
# Android capture through the Mac's shared Wi-Fi (experiment 059). The Mac records on its Internet Sharing bridge.
#   bash src/capture_android.sh check     signature check: 5 min Facebook, 5 min Instagram (059)
#   bash src/capture_android.sh long      full group: idle, 20 min Facebook/Instagram/YouTube, idle
# Path: iPhone Personal Hotspot (cellular) --USB--> Mac --Internet Sharing over Wi-Fi--> Android.
# Raw files stay in the gitignored data/captures/raw/. No address is printed or saved by this script.
set -u
cd "$(dirname "$0")/.." || exit 1
umask 077
PLAN=${1:-check}
BRIDGE=${BRIDGE:-bridge100}

clear
cat <<'TXT'
=== Android capture through the Mac's Wi-Fi ===

A. iPhone = internet for the Mac (cellular, because the home Wi-Fi blocks QUIC):
   1. iPhone: Settings > Personal Hotspot > Allow Others to Join: ON. Cellular data ON.
   2. Plug the iPhone into the Mac with the USB cable, unlock it, tap Trust if asked.
   3. Mac: System Settings > Network: "iPhone USB" should show Connected (green).

B. Mac = Wi-Fi network for the Android phone:
   4. Mac: System Settings > General > Sharing > Internet Sharing > click (i):
        Share your connection from: iPhone USB
        To devices using: Wi-Fi  -> Wi-Fi Options: name "SidMac-capture", security WPA2/WPA3, choose a password
      Click Done, then switch Internet Sharing ON (confirm Start).
      (The Mac leaves the home Wi-Fi; its internet now comes from the iPhone.)

C. Android phone:
   5. Mobile data OFF (so every app uses the Mac's Wi-Fi). VPN OFF.
   6. Wi-Fi: join "SidMac-capture".
   7. Close Facebook and Instagram (Recent apps > swipe them away). Screen timeout: 10 minutes or longer.
   8. Open a web page once to check the internet works.
TXT
read -r -p "Press Enter when A, B and C are done... " _

WIFI_RE='ap[0-9]+|'"$(networksetup -listallhardwareports | awk '/Hardware Port: Wi-Fi/{getline; print $2}')"  # macOS shares Wi-Fi via ap1
clients() { arp -an -i "$BRIDGE" 2>/dev/null | grep -v -e incomplete -e permanent -e '\.255)' | grep -v -E '\((22[4-9]|23[0-9])\.' | grep -c "on $BRIDGE"; }
if ! ifconfig "$BRIDGE" >/dev/null 2>&1; then
  echo "$BRIDGE not found: Internet Sharing is not on (step 4). Turn it on, then run this script again."
  exit 1
fi
if ! ifconfig "$BRIDGE" | grep -q -E "member: ($WIFI_RE) "; then
  echo "Internet Sharing is on, but NOT over Wi-Fi (no Wi-Fi interface in $BRIDGE)."
  echo "Turn Internet Sharing OFF, then in its (i) settings tick ONLY Wi-Fi under 'To devices using'"
  echo "(untick every LAN/Ethernet/Thunderbolt entry), turn it back ON, and run this script again."
  exit 1
fi
OTHERS=$(ifconfig "$BRIDGE" | awk '/member:/{print $2}' | grep -v -E "^($WIFI_RE)$" | tr '\n' ' ')
if [ -n "$OTHERS" ]; then
  echo "Warning: Internet Sharing also serves wired ports ($OTHERS). Untick them so only the Android phone is on this network."
  read -r -p "Press Enter to continue anyway, or Ctrl-C to fix it first... " _
fi
USBDEV=$(networksetup -listnetworkserviceorder | awk '/iPhone USB/{getline; print}' | sed -n 's/.*Device: \([^)]*\)).*/\1/p')
DEF=$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')
if [ -z "$USBDEV" ] || [ "$DEF" != "$USBDEV" ]; then
  echo "Warning: the Mac's internet does not go through iPhone USB (default: ${DEF:-none}, iPhone USB: ${USBDEV:-not found})."
  read -r -p "Fix step A (or press Enter to continue anyway)... " _
fi
n=$(clients)
until [ "$n" -gt 0 ]; do
  read -r -p "No device on the Mac's Wi-Fi yet. Join \"SidMac-capture\" on the Android phone, then press Enter... " _
  n=$(clients)
done
echo "Devices on the Mac's Wi-Fi: $n (should be 1: the Android phone)."

ROOT="$PWD/data/captures/raw/sid-android-$(date -u +%Y%m%dT%H%M%SZ)-$PLAN-macshare"
mkdir -p "$ROOT" || exit 1
printf '%s\n' "$ROOT" > data/captures/raw/latest-sid-capture-root.txt
{ date -u +%FT%TZ; sw_vers; /usr/sbin/tcpdump --version; git rev-parse HEAD; df -h .; echo "bridge: $BRIDGE"; echo "upstream: $DEF (iPhone USB: $USBDEV)"; echo "devices on bridge: $n"; } > "$ROOT/setup.txt" 2>&1
cat > "$ROOT/environment.md" <<ENV
# Environment: $(basename "$ROOT")

- Mac: $(sysctl -n hw.model), macOS $(sw_vers -productVersion); capture on the Internet Sharing bridge ($BRIDGE), \`/usr/sbin/tcpdump\`.
- Path: iPhone Personal Hotspot (cellular) over USB -> Mac -> Internet Sharing over Wi-Fi -> Android.
- Android phone model: FILL IN · Android version: FILL IN
- Facebook version: FILL IN · Instagram version: FILL IN (Play Store > app > About this app)
- Android mobile data: FILL IN (should be OFF) · VPN: FILL IN · Private DNS: FILL IN (Settings > Network > Private DNS)
- iPhone signal for the hotspot (4G/5G): FILL IN
- Apps closed before their session: FILL IN · Logged in: FILL IN
- What you did in each app: FILL IN
- Anything unusual: FILL IN
ENV
echo "Group folder: $ROOT"
caffeinate -dimsu &
CAF=$!
trap 'kill $CAF 2>/dev/null' EXIT

SID_RVI="$BRIDGE" PLAN="$PLAN" bash src/capture_pilot.sh
status=$?
echo
if [ $status -eq 0 ]; then
  echo "All done. You can turn Internet Sharing OFF and reconnect the Mac to your Wi-Fi."
  echo "Then fill in the FILL IN lines of $ROOT/environment.md (or paste the answers to Claude)."
  echo "Tell Claude: 'android $PLAN done'."
else
  echo "The run stopped early (status $status). Do not start another recording. Copy this window's text to Claude."
fi
