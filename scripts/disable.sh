#!/bin/sh
set -eu
BASE=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
. "$BASE/scripts/common.sh"
device_check
"$ADB" shell 'su -c "resetprop persist.epd.tenmin.test 0; resetprop persist.epd.tenmin 0; resetprop persist.epd.autoclock 0; resetprop persist.epd.liveclock 0"'
echo "Dynamic calendar power-key and auto-idle overrides OFF; stock sleep restored."
