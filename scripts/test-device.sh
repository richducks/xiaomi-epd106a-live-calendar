#!/bin/sh
set -eu
BASE=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
. "$BASE/scripts/common.sh"
device_check
echo "DEVICE: $("$ADB" shell getprop ro.product.model | tr -d '\r')"
echo "CURRENT: $("$ADB" shell dumpsys window | grep -m1 mCurrentFocus || true)"
echo "LIVE_SWITCH: $("$ADB" shell getprop persist.epd.liveclock | tr -d '\r')"
"$ADB" shell pm path org.epd.calendar
"$ADB" shell pm path org.epd.calendar.policy
[ "${1:-}" = "--power-cycle" ] || { echo "READ-ONLY CHECK COMPLETE; use --power-cycle only with explicit user acceptance"; exit 0; }
[ "$("$ADB" shell getprop persist.epd.liveclock | tr -d '\r')" = "1" ] || { echo "ERROR: hook switch is OFF" >&2; exit 1; }
before=$("$ADB" shell pidof system_server | tr -d '\r')
focus=$("$ADB" shell dumpsys window | grep -m1 mCurrentFocus)
echo "$focus" | grep -q UsbMtpAcitivity || { echo "ERROR: refusing to disrupt the user's active reader/other app. Open Settings USB screen first." >&2; exit 1; }
# Real Android key events, not /dev/input EVIOCGRAB or uinput.
"$ADB" shell input keyevent KEYCODE_POWER
sleep 2
"$ADB" shell dumpsys window | grep -m1 mCurrentFocus | grep -q org.epd.calendar || { echo "FAIL first press"; "$ADB" shell input keyevent KEYCODE_WAKEUP || true; exit 1; }
"$ADB" shell input keyevent KEYCODE_POWER
sleep 2
"$ADB" shell dumpsys window | grep -m1 mCurrentFocus | grep -q UsbMtpAcitivity || { echo "FAIL second press"; "$ADB" shell input keyevent KEYCODE_WAKEUP || true; exit 1; }
[ "$before" = "$("$ADB" shell pidof system_server | tr -d '\r')" ] || { echo "FAIL system_server restarted" >&2; exit 1; }
echo "PASS: open/close dynamic calendar, restored prior task, system_server stable"
