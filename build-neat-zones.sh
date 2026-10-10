#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
SDK="${ANDROID_HOME:-$HOME/Android/Sdk}"
API="$SDK/platforms/android-36/android.jar"
BT="$SDK/build-tools/35.0.0"
rm -rf build/neat-stubs build/neat-classes build/neat-dex build/neat-apk
mkdir -p build/neat-stubs build/neat-classes build/neat-dex build/neat-apk/assets build/output
find xposed/compile-stubs -name '*.java' > build/neat-stub-sources.txt
javac -encoding UTF-8 -source 8 -target 8 -cp "$API" -d build/neat-stubs @build/neat-stub-sources.txt
jar cf build/neat-xposed-stubs.jar -C build/neat-stubs .
javac -encoding UTF-8 -source 8 -target 8 -cp "$API:build/neat-xposed-stubs.jar" -d build/neat-classes neat-zones/src/org/epd/neat/touchzones/NeatTouchZones.java
"$BT/d8" --min-api 26 --lib "$API" --output build/neat-dex build/neat-classes/org/epd/neat/touchzones/NeatTouchZones*.class
"$BT/aapt2" link -o build/neat-base.apk --manifest neat-zones/AndroidManifest.xml -I "$API" --min-sdk-version 26 --target-sdk-version 27
cp build/neat-dex/classes.dex build/neat-apk/classes.dex
echo org.epd.neat.touchzones.NeatTouchZones > build/neat-apk/assets/xposed_init
(cd build/neat-apk && zip -q -u ../neat-base.apk classes.dex assets/xposed_init)
"$BT/zipalign" -f 4 build/neat-base.apk build/neat-aligned.apk
"$BT/apksigner" sign --ks "$HOME/.android/debug.keystore" --ks-pass pass:android --key-pass pass:android --out build/output/eink-neat-touchzones.apk build/neat-aligned.apk
"$BT/apksigner" verify --verbose build/output/eink-neat-touchzones.apk
echo BUILT_NEAT_TOUCHZONES_APK_OK
