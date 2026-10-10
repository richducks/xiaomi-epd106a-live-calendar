#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
SDK="${ANDROID_HOME:-$HOME/Android/Sdk}"
API="$SDK/platforms/android-36/android.jar"
BT="$SDK/build-tools/35.0.0"
rm -rf build/xposed-stubs build/xposed-classes build/xposed-dex build/xposed-apk
mkdir -p build/xposed-stubs build/xposed-classes build/xposed-dex build/xposed-apk/assets build/output
find xposed/compile-stubs -name '*.java' > build/xposed-stub-sources.txt
javac -encoding UTF-8 -source 8 -target 8 -cp "$API" -d build/xposed-stubs @build/xposed-stub-sources.txt
jar cf build/xposed-api-compile-only.jar -C build/xposed-stubs .
javac -encoding UTF-8 -source 8 -target 8 -cp "$API:build/xposed-api-compile-only.jar" -d build/xposed-classes xposed/src/org/epd/calendar/policy/PowerPolicyHook.java
"$BT/d8" --min-api 26 --lib "$API" --output build/xposed-dex build/xposed-classes/org/epd/calendar/policy/PowerPolicyHook*.class
"$BT/aapt2" link -o build/xposed-base.apk --manifest xposed/AndroidManifest.xml -I "$API" --min-sdk-version 26 --target-sdk-version 27
cp build/xposed-dex/classes.dex build/xposed-apk/classes.dex
echo org.epd.calendar.policy.PowerPolicyHook > build/xposed-apk/assets/xposed_init
(cd build/xposed-apk && zip -q -u ../xposed-base.apk classes.dex assets/xposed_init)
"$BT/zipalign" -f 4 build/xposed-base.apk build/xposed-aligned.apk
"$BT/apksigner" sign --ks "$HOME/.android/debug.keystore" --ks-pass pass:android --key-pass pass:android --out build/output/eink-livecalendar-policy.apk build/xposed-aligned.apk
"$BT/apksigner" verify --verbose build/output/eink-livecalendar-policy.apk
printf 'BUILT_XPOSED_LEGACY_APK_OK\n'
