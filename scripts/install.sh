#!/bin/sh
set -eu
BASE=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
. "$BASE/scripts/common.sh"
device_check
APP="$BASE/build/output/eink-calendar-test.apk"
HOOK="$BASE/build/output/eink-livecalendar-policy.apk"
[ -f "$APP" ] && [ -f "$HOOK" ] || { echo "Build both APKs first: bash build.sh && bash build-xposed.sh" >&2; exit 1; }
# Install an independent Recovery guard before any system-server hooking.
# Never overwrite an existing locally maintained guard without review.
"$ADB" push "$BASE/recovery/00-eink-livecalendar-recovery-guard.sh" /data/local/tmp/00-eink-livecalendar-recovery-guard.sh
"$ADB" shell 'su -c "mkdir -p /data/adb/post-fs-data.d; if [ ! -e /data/adb/post-fs-data.d/00-eink-livecalendar-recovery-guard.sh ]; then cp /data/local/tmp/00-eink-livecalendar-recovery-guard.sh /data/adb/post-fs-data.d/00-eink-livecalendar-recovery-guard.sh; chmod 0700 /data/adb/post-fs-data.d/00-eink-livecalendar-recovery-guard.sh; fi"'
"$ADB" shell 'su -c "test -f /data/adb/post-fs-data.d/00-eink-livecalendar-recovery-guard.sh"' || { echo "ERROR: Recovery guard missing" >&2; exit 1; }
# Safety: never start newly installed policy while system is still configuring.
"$ADB" shell 'su -c "resetprop persist.epd.liveclock 0"'
"$ADB" install -r "$APP"
"$ADB" install -r "$HOOK"
"$ADB" shell pm path org.epd.calendar
"$ADB" shell pm path org.epd.calendar.policy
echo "INSTALLED (disabled). Configure LSPosed scope: Android Framework/system only; reboot, then bash scripts/enable.sh"
echo "NOTICE: enable.sh does not configure LSPosed automatically."
