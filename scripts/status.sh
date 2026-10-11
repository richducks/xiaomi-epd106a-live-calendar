#!/bin/sh
set -eu
BASE=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
. "$BASE/scripts/common.sh"
device_check
echo "model: $("$ADB" shell getprop ro.product.model | tr -d '\r')"
echo "boot_completed: $("$ADB" shell getprop sys.boot_completed | tr -d '\r')"
echo "liveclock_property: $("$ADB" shell getprop persist.epd.liveclock | tr -d '\r')"
echo "autoclock_property: $("$ADB" shell getprop persist.epd.autoclock | tr -d '\r')"
"$ADB" shell pm path org.epd.calendar
"$ADB" shell pm path org.epd.calendar.policy
"$ADB" shell 'su -c "test -f /data/adb/post-fs-data.d/00-eink-livecalendar-recovery-guard.sh && echo GUARD_PRESENT || echo GUARD_MISSING"'
"$ADB" shell 'su -c "test -e /cache/eink-calendar-rescue.disable && echo RECOVERY_DISABLE_ACTIVE || echo RECOVERY_DISABLE_CLEAR"'
"$ADB" shell dumpsys power | grep -E 'mWakefulness=|Display Power: state='
echo "Physical-power-key/long-press and battery life require real-device acceptance."
