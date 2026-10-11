#!/bin/sh
set -eu
BASE=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
. "$BASE/scripts/common.sh"
device_check
"$ADB" shell dumpsys package org.epd.calendar.policy | grep -q 'versionName=0.3.0-alpha.2' || { echo 'ERROR: install matching experimental policy APK first' >&2; exit 1; }
"$ADB" shell dumpsys package org.epd.calendar | grep -q 'versionName=0.3.0-alpha.2' || { echo 'ERROR: install matching experimental calendar APK first' >&2; exit 1; }
"$ADB" shell 'su -c "test -f /data/adb/post-fs-data.d/00-eink-livecalendar-recovery-guard.sh"' || { echo 'ERROR: missing recovery guard' >&2; exit 1; }
"$ADB" shell 'su -c "resetprop persist.epd.tenmin.test 0; resetprop persist.epd.tenmin 1; resetprop persist.epd.autoclock 1; resetprop persist.epd.liveclock 1"'
echo 'EXPERIMENT enabled: 10-minute RTC updates with real Android suspend. Exit any open clock, then let auto-idle launch a fresh clock. Run bash scripts/status.sh'
