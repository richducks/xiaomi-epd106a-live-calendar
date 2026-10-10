#!/usr/bin/env bash
# Read-only offline checkpoint of the currently running EPD106A.
# NEVER contains any raw flash/erase or APK installation operations.
set -euo pipefail
umask 077
OUT_ROOT="${EPD_PRIVATE_BACKUP_DIR:-$HOME/EPD106A-private-backups}"
REUSE=''
INCLUDE_PRIVATE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --reuse) [[ $# -ge 2 ]] || exit 2; REUSE="$2"; shift 2;;
    --include-private-data) INCLUDE_PRIVATE=1; shift;;
    *) echo 'Usage: bash scripts/snapshot-private.sh [--reuse DIR] [--include-private-data]' >&2; exit 2;;
  esac
done
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if command -v adb >/dev/null 2>&1; then ADB=adb
elif [[ -x "${ANDROID_HOME:-$HOME/Android/Sdk}/platform-tools/adb" ]]; then ADB="${ANDROID_HOME:-$HOME/Android/Sdk}/platform-tools/adb"
else echo 'ERROR: adb missing' >&2; exit 1; fi
count="$("$ADB" devices | awk 'NR>1 && $2=="device" {n++} END {print n+0}')"
[[ "$count" == 1 ]] || { echo 'ERROR: exactly one authorized ADB device' >&2; exit 1; }
prop(){ "$ADB" shell getprop "$1" | tr -d '\r'; }
[[ "$(prop ro.product.model)" == EPD106A && "$(prop ro.product.device)" == virgo-perf1 ]] || { echo 'ERROR: wrong device' >&2; exit 1; }
[[ "$(prop ro.build.fingerprint)" == 'Allwinner/virgo_perf1/virgo-perf1:8.1.0/OPM1.171019.026/20240424-143400:user/test-keys' ]] || { echo 'ERROR: unverified firmware' >&2; exit 1; }
"$ADB" shell 'su -c id' | grep -q uid=0 || { echo 'ERROR: root required' >&2; exit 1; }
[[ ! -L "$OUT_ROOT" ]] || { echo 'ERROR: backup root cannot be a symlink' >&2; exit 1; }
mkdir -p "$OUT_ROOT"; chmod 700 "$OUT_ROOT"
OUT="$OUT_ROOT/checkpoint-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$OUT"; mkdir "$OUT/partitions" "$OUT/first-party-apks" "$OUT/private-config"
printf '%s\n' 'INCOMPLETE - verification pending' > "$OUT/INCOMPLETE"
printf 'model=%s\ndevice=%s\nfirmware=%s\nandroid=%s\nliveclock=%s\nneatzones=%s\n' \
  "$(prop ro.product.model)" "$(prop ro.product.device)" "$(prop ro.build.fingerprint)" \
  "$(prop ro.build.version.release)" "$(prop persist.epd.liveclock)" "$(prop persist.epd.neatzones)" > "$OUT/private-config/device-properties.txt"
"$ADB" shell pm list packages -3 > "$OUT/private-config/installed-third-party-package-ids.txt"
for part in boot recovery system vendor; do
  target="$OUT/partitions/$part.img"
  block="/dev/block/by-name/$part"
  echo "Reading current $part SHA-256 from device (read-only) ..."
  live="$("$ADB" shell "su -c 'dd if=$block bs=1048576 2>/dev/null | sha256sum'" | awk 'NR==1 {print $1}' | tr -d '\r')"
  [[ "$live" =~ ^[a-f0-9]{64}$ ]] || { echo "ERROR: cannot hash device $part" >&2; exit 1; }
  if [[ -n "$REUSE" ]]; then
    src="$REUSE/$part.img"
    if [[ ! -f "$src" && -f "$REUSE/partitions/$part.img" ]]; then src="$REUSE/partitions/$part.img"; fi
    [[ -f "$src" && ! -L "$src" ]] || { echo "ERROR: reusable image missing: $part" >&2; exit 1; }
    [[ "$(sha256sum "$src" | cut -d' ' -f1)" == "$live" ]] || { echo "ERROR: reusable $part differs from live device" >&2; exit 1; }
    cp --reflink=auto -- "$src" "$target"
  else
    "$ADB" exec-out su -c "dd if=$block bs=1048576 2>/dev/null" > "$target.partial"
    [[ "$(sha256sum "$target.partial" | cut -d' ' -f1)" == "$live" ]] || { echo "ERROR: $part transfer checksum mismatch" >&2; exit 1; }
    mv "$target.partial" "$target"
  fi
  chmod 600 "$target"
done
# Sensitive app/Root databases and personal books are OFF by default.
# Opt in explicitly on a personally controlled encrypted backup disk.
if [[ "$INCLUDE_PRIVATE" == 1 ]]; then
  echo 'WARNING: this local archive will contain Root settings, private login data and personal books. Never upload/share it.'
  "$ADB" exec-out su -c 'tar -cf - -C / data/adb/modules data/adb/lspd/config data/adb/magisk.db data/adb/post-fs-data.d data/adb/service.d data/adb/eink-calendar' | gzip -6 > "$OUT/private-config/root-lsposed-settings.tar.gz"
  gzip -t "$OUT/private-config/root-lsposed-settings.tar.gz"
  "$ADB" exec-out su -c 'tar -cf - -C / data/user/0/com.gzhi.neatreader.r2.main data/media/0' | gzip -6 > "$OUT/private-config/reader-books-and-login-PRIVATE.tar.gz"
  gzip -t "$OUT/private-config/reader-books-and-login-PRIVATE.tar.gz"
fi
for spec in 'org.epd.calendar eink-calendar' 'org.epd.calendar.policy eink-livecalendar-policy' 'org.epd.neat.touchzones eink-neat-touchzones'; do
  read -r pkg name <<< "$spec"
  apk="$("$ADB" shell pm path "$pkg" | sed -n '1s/^package://p' | tr -d '\r')"
  [[ "$apk" == /* ]] || { echo "ERROR: missing $pkg" >&2; exit 1; }
  "$ADB" pull "$apk" "$OUT/first-party-apks/$name.apk" >/dev/null
done
chmod 600 "$OUT"/private-config/* "$OUT"/first-party-apks/*
(cd "$OUT" && sha256sum partitions/*.img first-party-apks/*.apk > SHA256SUMS && if [[ "$INCLUDE_PRIVATE" == 1 ]]; then sha256sum private-config/*.tar.gz >> SHA256SUMS; fi && sha256sum --check SHA256SUMS)
printf '%s\n' 'COMPLETE: verified same-device partitions, first-party APKs, package/configuration manifest; extra private app data only when explicitly requested.' \
  'NOT VERIFIED: bootable end-to-end restore or portable user-account clone.' > "$OUT/RESTORE-READ-ME.txt"
rm "$OUT/INCOMPLETE"
echo "CHECKPOINT_VERIFIED_PRIVATE: $OUT"
echo 'Keep encrypted OFFLINE copies; never add this folder to GitHub.'
