#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 1 ] || { [ "$1" != "1" ] && [ "$1" != "10" ]; }; then
  echo "Usage: $0 1|10 (minutes)" >&2
  exit 2
fi
ADB="$HOME/Android/Sdk/platform-tools/adb"
"$ADB" get-state >/dev/null
"$ADB" shell "su -c 'setprop persist.epd.clock.interval $1'"
actual="$("$ADB" shell getprop persist.epd.clock.interval | tr -d '\r')"
if [ "$actual" != "$1" ]; then
  echo "Failed to set RTC cadence; current: $actual" >&2
  exit 1
fi
echo "RTC calendar interval = $1 minute(s). Applies next alarm; reopen calendar for immediate effect."
