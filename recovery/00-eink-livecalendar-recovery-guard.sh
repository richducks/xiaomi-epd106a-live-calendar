#!/system/bin/sh
# Verified EPD106A Recovery writes only /cache marker.
# This guard runs at early Magisk post-fs-data; can disable both the calendar
# Magisk payload and the separately packaged official LSPosed runtime.
MARK=/cache/eink-calendar-rescue.disable
LOG=/cache/eink-calendar-rescue.log
[ -r "$MARK" ] || exit 0
VALUE="$(cat "$MARK" 2>/dev/null)"
[ "$VALUE" = "DISABLE_EINK_CALENDAR_V1" ] || exit 0
for ID in eink-livecalendar zygisk_lsposed; do
  TARGET="/data/adb/modules/$ID"
  [ -d "$TARGET" ] || continue
  [ -f "$TARGET/module.prop" ] || continue
  : > "$TARGET/disable"
  if [ -f "$TARGET/disable" ]; then
    echo "EINK_CALENDAR_RECOVERY_DISABLE_OK $ID" >> "$LOG"
  else
    echo "EINK_CALENDAR_RECOVERY_DISABLE_FAILED $ID" >> "$LOG"
  fi
done
exit 0
