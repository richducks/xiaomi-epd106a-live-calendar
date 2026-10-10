#!/bin/sh
set -eu
BASE=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
. "$BASE/scripts/common.sh"
device_check
"$ADB" shell pm path org.epd.calendar | grep -q 'package:' || { echo "ERROR: Native app missing" >&2; exit 1; }
"$ADB" shell pm path org.epd.calendar.policy | grep -q 'package:' || { echo "ERROR: LSPosed policy APK missing" >&2; exit 1; }
"$ADB" shell 'su -c "test -f /data/adb/modules/zygisk_lsposed/module.prop"' || { echo "ERROR: LSPosed missing" >&2; exit 1; }
"$ADB" shell 'su -c "test -f /data/adb/post-fs-data.d/00-eink-livecalendar-recovery-guard.sh"' || { echo "ERROR: Recovery guard not installed; see docs/RECOVERY.md" >&2; exit 1; }
"$ADB" shell 'su -c "test ! -f /cache/eink-calendar-rescue.disable"' || { echo "ERROR: recovery emergency disable is active" >&2; exit 1; }
echo "WARNING: Ensure LSPosed module org.epd.calendar.policy is scoped to Android Framework/system; reboot after new installation."
"$ADB" shell 'su -c "resetprop persist.epd.liveclock 1"'
echo "Enabled (requires hook already loaded at boot). Run bash scripts/status.sh"
