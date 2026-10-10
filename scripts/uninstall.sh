#!/bin/sh
set -eu
BASE=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
. "$BASE/scripts/common.sh"
device_check
echo "Uninstall ONLY the independent calendar APK + policy module, not books or reader apps."
printf "Type UNINSTALL to continue: "
read answer
[ "$answer" = "UNINSTALL" ] || { echo "Cancelled"; exit 0; }
"$ADB" shell 'su -c "resetprop persist.epd.liveclock 0"'
"$ADB" uninstall org.epd.calendar.policy || true
"$ADB" uninstall org.epd.calendar || true
echo "Calendar APKs uninstalled. Reboot to unload cached framework hook."
echo "Independent Recovery guard remains for safety (can be removed later after full verification)."
