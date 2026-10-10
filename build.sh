#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
SDK="${ANDROID_HOME:-$HOME/Android/Sdk}"
BT="$SDK/build-tools/35.0.0"
API="$SDK/platforms/android-36/android.jar"
mkdir -p build/output
# Prevent stale experimental .class/.dex files from entering release APK.
rm -rf build/classes build/dex
mkdir -p build/classes build/dex
javac -encoding UTF-8 -source 8 -target 8 -cp "$API" -d build/classes src/org/epd/calendar/MainActivity.java src/org/epd/calendar/BrushRingDrawable.java
"$BT/d8" --min-api 26 --lib "$API" --output build/dex $(find build/classes -type f -name '*.class')
"$BT/aapt2" link -o build/base.apk --manifest AndroidManifest.xml -I "$API" --min-sdk-version 26 --target-sdk-version 27
(cd build/dex && zip -q -u ../base.apk classes.dex)
"$BT/zipalign" -f 4 build/base.apk build/aligned.apk
KEY="$HOME/.android/debug.keystore"
if [[ ! -f "$KEY" ]];then
  mkdir -p "$HOME/.android"
  keytool -genkeypair -keystore "$KEY" -storepass android -alias androiddebugkey -keypass android -dname "CN=Android Debug,O=Android,C=US" -keyalg RSA -keysize 2048 -validity 10000 -noprompt
fi
"$BT/apksigner" sign --ks "$KEY" --ks-pass pass:android --key-pass pass:android --out build/output/eink-calendar-test.apk build/aligned.apk
"$BT/apksigner" verify --verbose build/output/eink-calendar-test.apk
ls -lh build/output/eink-calendar-test.apk
