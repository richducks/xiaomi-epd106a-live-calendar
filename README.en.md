# Ink Calendar — native live lockscreen for Xiaomi EPD106A

An independently developed Android 8.1 application and optional LSPosed power-policy module for the Xiaomi/Duokan EPD106A e-reader running Moan firmware. Shows live Beijing-time HH:mm with Chinese lunar dates, a monthly calendar, estimated solar terms and a hand-drawn marker around today. A short power press opens the live calendar; pressing again restores the previous task.

**This is not deep-sleep AOD:** the display remains ON for minute-by-minute updates and uses more power than the original static sleep screen. Power-saving thresholds are built in, but actual battery drain has not been fully measured.

See [Chinese installation instructions](docs/INSTALL.md), [verification](docs/ACCEPTANCE.md), [recovery](docs/RECOVERY.md), and [firmware redistribution policy](docs/ROOT_AND_LICENSES.md).

Build with JDK and Android SDK (android-36, build-tools 35.0.0): `bash build.sh && bash build-xposed.sh`. Android and LSPosed APKs are independently developed. **No proprietary stock firmware, root boot image, DRM content or third-party binary is bundled.**

Licensed Apache-2.0 for the first-party source only. Tested on EPD106A Android 8.1 only.
