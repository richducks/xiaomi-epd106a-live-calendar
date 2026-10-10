#!/bin/sh
set -eu
BASE=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
. "$BASE/scripts/common.sh"
device_check
"$ADB" shell 'su -c "resetprop persist.epd.liveclock 0"'
echo "Dynamic calendar power-button override OFF; original short press will sleep."
