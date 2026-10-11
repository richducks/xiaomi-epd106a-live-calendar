#!/bin/sh
set -eu
BASE=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
. "$BASE/scripts/common.sh"
device_check
"$ADB" shell 'su -c "resetprop persist.epd.tenmin.test 0; resetprop persist.epd.tenmin 0"'
echo '10-minute experiment OFF. Existing live calendar modes remain enabled. Exit/reopen clock to restore normal behavior.'
