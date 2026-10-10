#!/bin/sh
set -eu
if command -v adb >/dev/null 2>&1; then ADB=adb
elif [ -x "${ANDROID_HOME:-$HOME/Android/Sdk}/platform-tools/adb" ]; then ADB="${ANDROID_HOME:-$HOME/Android/Sdk}/platform-tools/adb"
else echo "ERROR: adb not found" >&2; exit 1; fi
device_check() {
  "$ADB" devices | grep -Eq '^[^[:space:]]+[[:space:]]+device$' || { echo "ERROR: Android device not connected and authorized" >&2; exit 1; }
  [ "$("$ADB" shell getprop ro.product.device | tr -d '\r')" = "virgo-perf1" ] || { echo "ERROR: EPD106A device required" >&2; exit 1; }
  [ "$("$ADB" shell getprop ro.build.version.sdk | tr -d '\r')" = "27" ] || { echo "ERROR: Android 8.1 API 27 required" >&2; exit 1; }
  "$ADB" shell 'su -c id' | grep -q 'uid=0' || { echo "ERROR: Root access required" >&2; exit 1; }
}
