# 安装、启动、停用和卸载

> ⚠ 系统级电源键模块仅验证于 EPD106A / Android 8.1。安装前保存原系统备份、书籍数据及有效的 Recovery 救援途径；不要从其他型号移植。

## 1. 前置条件

确认 Ubuntu ADB 已连接，`adb devices` 为 device，阅读器 `getprop ro.product.device` 为 `virgo-perf1`，Android SDK 为 27，Root `su -c id` 返回 uid=0。设备安装受信任来源的 Magisk（Zygisk 开启）和 LSPosed。**不要把这些第三方组件与本项目仓库内源码混淆。**

Recovery 救援：请先阅读 [RECOVERY.md](RECOVERY.md)，安装独立于 LSPosed 的开机回退护栏，验证紧急标记渠道可以恢复后，再启用 system hook。缺少这些条件不要继续。

## 2. 安装

下载安装：从 [GitHub Release](https://github.com/richducks/xiaomi-epd106a-live-calendar/releases) 下载 `eink-calendar.apk` 和 `eink-livecalendar-policy.apk` 到仓库的 `dist/` 文件夹。或者在仓库根目录执行 `bash build.sh && bash build-xposed.sh`。脚本会优先使用 `dist/` 内下载的 APK，然后才回退到源码编译结果。

```bash
mkdir -p dist
# 下载好的两份 APK 放在 dist/ 后运行
bash scripts/install.sh
```

脚本先检查机型、安卓 API、Root、安装包存在，再安装两份 APK，确保动态电源键开关默认关闭。不会刷 boot/system/vendor 或卸载阅读器软件。

## 3. LSPosed 配置（需要在设备上完成）

打开 LSPosed 管理器，勾选 **墨水万年历 · 电源键模块**（org.epd.calendar.policy），作用域只选 **Android Framework / system**，不要选择多看、其他第三方 App 或系统设置，之后重启阅读器。没有成功装载系统策略钩子时，`enable.sh` 无法自动代替这一步。

## 4. 体验和验收

在 Ubuntu 中执行 `bash scripts/enable.sh`，检查 `bash scripts/status.sh`。打开阅读器的一本书，短按真实实体电源键进入动态日历；停留跨过整分钟，确认 HH:mm 变化；再次短按，确认返回原书籍页码。

打开时不出现旧 PNG 是设计目标；是否在所有电量和操作序列无残影仍需实机确认。可以直接点击日历返回。长按关机保留原生系统逻辑。

## 5. 停止、升级和卸载

`bash scripts/disable.sh` **立即关闭功能**，原生系统电源键行为保持正常。升级先关闭、用同签名证书重新构建/安装、重启并复测；签名不同可能无法原位更新，先备份设置。签名密钥从不在 GitHub 公开。

`bash scripts/uninstall.sh` 在取得交互确认后卸载两份 APK 和本项目早期恢复护栏；不会删除多看、书籍目录、厂商固件或 Magisk/LSPosed 本体。建议先验证系统正常，再卸载独立的恢复护栏。

## 6. 一键故障回退

Android 还能启动时：`bash scripts/disable.sh`。如无法进入系统，进入 Recovery → Apply update from ADB，使用[自建/已验证签名的救援包](RECOVERY.md)写入 /cache 标志，重启后保护脚本禁用 LSPosed。**不可使用本仓库之外来源不明的救援包。**
