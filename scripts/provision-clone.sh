#!/usr/bin/env bash
# EPD106A post-flash provisioning; deliberately never flashes firmware.
set -euo pipefail
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE_FINGERPRINT='Allwinner/virgo_perf1/virgo-perf1:8.1.0/OPM1.171019.026/20240424-143400:user/test-keys'
TAG='v0.2.0-restore-kit.1'
REPO='richducks/xiaomi-epd106a-live-calendar'
MODE="${1:---check}"
case "$MODE" in --check|--install|--activate) ;; *) echo 'Usage: bash scripts/provision-clone.sh [--check|--install|--activate]' >&2; exit 2;; esac
if command -v adb >/dev/null 2>&1; then ADB=adb
elif [[ -x "${ANDROID_HOME:-$HOME/Android/Sdk}/platform-tools/adb" ]]; then ADB="${ANDROID_HOME:-$HOME/Android/Sdk}/platform-tools/adb"
else echo 'ERROR: adb not found' >&2; exit 1; fi
# Never silently choose one device when several are plugged in.
count="$("$ADB" devices | awk 'NR>1 && $2=="device" {n++} END {print n+0}')"
[[ "$count" == 1 ]] || { echo "ERROR: exactly one authorized ADB device required (found $count)" >&2; exit 1; }
prop(){ "$ADB" shell getprop "$1" | tr -d '\r'; }
assert_device(){
  [[ "$(prop ro.product.model)" == EPD106A && "$(prop ro.product.device)" == virgo-perf1 ]] || { echo 'ERROR: not EPD106A / virgo-perf1' >&2; exit 1; }
  [[ "$(prop ro.build.version.sdk)" == 27 ]] || { echo 'ERROR: Android SDK 27 required' >&2; exit 1; }
  [[ "$(prop ro.build.fingerprint)" == "$PROFILE_FINGERPRINT" ]] || { echo 'ERROR: firmware build differs from verified 20240424-143400; DO NOT apply this profile' >&2; exit 1; }
  "$ADB" shell 'su -c id' | grep -q 'uid=0' || { echo 'ERROR: preinstall Magisk/root first' >&2; exit 1; }
}
has_package(){ "$ADB" shell pm path "$1" | grep -q '^package:'; }
assert_prereqs(){
  "$ADB" shell 'su -c "test -f /data/adb/modules/zygisk_lsposed/module.prop"' || { echo 'ERROR: install official LSPosed module (Zygisk), reboot, then retry' >&2; exit 1; }
  has_package com.topjohnwu.magisk || { echo 'ERROR: install matching official Magisk 30.7 APK' >&2; exit 1; }
}
check(){
  echo "DEVICE: $(prop ro.product.model) / $(prop ro.build.version.release) / $(prop ro.build.version.incremental)"
  echo "ROOT: available; LSPosed module: installed"
  for package in org.epd.calendar org.epd.calendar.policy org.epd.neat.touchzones com.gzhi.neatreader.r2.main io.github.muntashirakon.AppManager; do
    if has_package "$package"; then echo "PACKAGE: installed $package"; else echo "PACKAGE: missing $package"; fi
  done
  echo "liveclock: $(prop persist.epd.liveclock) | neat-zones: $(prop persist.epd.neatzones)"
  echo 'REQUIRED SCOPES: org.epd.calendar.policy -> Android Framework; org.epd.neat.touchzones -> NeatReader only.'
}
assert_device
assert_prereqs
if [[ "$MODE" == --check ]]; then check; exit 0; fi
if [[ "$MODE" == --install ]]; then
  # Exact first-party APKs: these pinned digests belong to this release only.
  mkdir -p "$BASE/dist"
  while read -r digest apk; do
    [[ -n "$digest" && "$apk" == *.apk && "$apk" != */* ]] || { echo "ERROR: invalid APK pin $apk" >&2; exit 1; }
    target="$BASE/dist/$apk"
    if [[ ! -f "$target" ]]; then
      echo "Downloading first-party package $apk from GitHub Release $TAG"
      curl --fail --location --retry 2 --silent --show-error -o "$target.partial" "https://github.com/$REPO/releases/download/$TAG/$apk"
      mv "$target.partial" "$target"
    fi
    printf '%s  %s\n' "$digest" "$target" | sha256sum --check --status || { echo "ERROR: hash mismatch: $apk" >&2; exit 1; }
  done < "$BASE/device/release-apks.sha256"
  # The recovery guard is installed BEFORE policy; do not overwrite custom copy.
  "$ADB" push "$BASE/recovery/00-eink-livecalendar-recovery-guard.sh" /data/local/tmp/00-eink-livecalendar-recovery-guard.sh >/dev/null
  "$ADB" shell 'su -c "mkdir -p /data/adb/post-fs-data.d; if [ ! -e /data/adb/post-fs-data.d/00-eink-livecalendar-recovery-guard.sh ]; then cp /data/local/tmp/00-eink-livecalendar-recovery-guard.sh /data/adb/post-fs-data.d/00-eink-livecalendar-recovery-guard.sh; chmod 0700 /data/adb/post-fs-data.d/00-eink-livecalendar-recovery-guard.sh; fi"'
  "$ADB" shell 'su -c "test -f /data/adb/post-fs-data.d/00-eink-livecalendar-recovery-guard.sh"' || { echo 'ERROR: recovery guard missing' >&2; exit 1; }
  # A newly installed system-server hook must not become active before scopes are configured.
  "$ADB" shell 'su -c "resetprop persist.epd.liveclock 0; resetprop persist.epd.neatzones 0"'
  for apk in eink-calendar.apk eink-livecalendar-policy.apk eink-neat-touchzones.apk; do
    "$ADB" install -r "$BASE/dist/$apk"
  done
  echo 'INSTALLED (BOTH FEATURES OFF). Configure LSPosed scopes, reboot once, then run --activate.'
  echo 'Install NeatReader 8.1.4 separately from a lawful source; it is NOT redistributed here.'
  exit 0
fi
# Explicit second phase: require scope confirmation; no DB modification.
for package in org.epd.calendar org.epd.calendar.policy org.epd.neat.touchzones com.gzhi.neatreader.r2.main; do
  has_package "$package" || { echo "ERROR: missing $package" >&2; exit 1; }
done
"$ADB" shell 'su -c "test -f /data/adb/post-fs-data.d/00-eink-livecalendar-recovery-guard.sh; test ! -e /cache/eink-calendar-rescue.disable"' || { echo 'ERROR: recovery guard absent or emergency disable active' >&2; exit 1; }
if [[ "${EPD_SCOPES_CONFIRMED:-}" != 'YES' ]]; then
  echo 'ERROR: in LSPosed manually enable org.epd.calendar.policy ONLY for Android Framework and org.epd.neat.touchzones ONLY for NeatReader, then reboot.' >&2
  echo 'After verifying scopes, run: EPD_SCOPES_CONFIRMED=YES bash scripts/provision-clone.sh --activate' >&2
  exit 1
fi
"$ADB" shell 'su -c "resetprop persist.epd.liveclock 1; resetprop persist.epd.neatzones 1"'
echo 'ACTIVATED. Reopen NeatReader and verify the power-key calendar and dual menus. If unstable: bash scripts/disable.sh and su -c "resetprop persist.epd.neatzones 0".'
