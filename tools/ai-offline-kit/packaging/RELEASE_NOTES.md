# 小米 EPD106A 跨平台工具箱 v0.3.1-beta.1

这是**电脑端可直接下载运行的测试版**，无需手动安装 Python。每个压缩包包含图形界面 `XiaomiReader` 和供具备本机终端权限的 AI 调用的 `XiaomiReaderAI`。

### 下载哪个包

- Windows 10/11 x64：`XiaomiReader-windows-x64-v0.3.1.zip`
- macOS Intel：`XiaomiReader-macos-x64-v0.3.1.zip`
- macOS Apple Silicon M1/M2/M3/M4：`XiaomiReader-macos-arm64-v0.3.1.zip`
- Linux x64 图形桌面：`XiaomiReader-linux-x64-v0.3.1.zip`
- EPD106A 自研应用旧实验版：`EPD106A-first-party-APKs-2026-10-11.zip`（历史 10 分钟 RTC 实验版，**不是** 2026-10-14 最新源码，也不是全系统部署包）。

解压完整 ZIP，Windows 双击 `启动_Windows.bat`，macOS 双击 `XiaomiReader.app`（未公证，可能需要手动允许），Linux 运行 `bash 启动_Linux.sh`。软件可以检查设备、备份、校验备份、在再次确认后向**同类型设备**恢复第三方 APK。不会刷 ROM、恢复 Root 服务或绕过厂商锁。

### 第一次使用必读

Google ADB/Fastboot **未预先包含在公开 ZIP**（需要遵守 Google SDK 许可）。应用内提供“下载官方 ADB”：只有用户阅读并接受 SDK 许可后，才会从 Google 官方服务器下载。可能需要 Windows 驱动、macOS 安全授权或 Linux udev/USB 权限。首次下载需要联网，之后可在同一电脑离线使用。

**现有自研 APK 是历史实验版本**，Root/LSPosed、精确的 EPD106A 固件指纹和模块作用域需要按仓库 `docs/SAME_DEVICE_RESTORE.md` 单独准备。若已经安装不同签名的同名 APK，Android 会拒绝覆盖；不要为解决签名冲突擅自卸载和清除数据。日历壁纸/省电策略/NeatReader 效果必须实机验收，绝不宣称“一键完整克隆”。

**安全性**：电脑端程序是开源项目的未经商业代码签名/Apple 公证的发布构建。请核对来源、下载包及 `SHA256SUMS.txt`；杀毒或 Gatekeeper 可能提示警告。不要绕过不明来源安全警告。下载链接来自此仓库正式 Release 页面。

**状态**：跨平台 CI 可验证构建、程序启动与模拟设备测试；USB、Magisk、LSPosed、设备真机部署依然需要独立验收。
