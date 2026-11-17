# 普通用户下载与安装：Windows / Mac / Linux

电脑版下载入口：**[GitHub Releases](https://github.com/richducks/xiaomi-epd106a-live-calendar/releases)**。请选择标题含“AI 跨平台阅读器工具箱”的版本；旧的 `v0.3.0-ten-minute-alpha.2` 是 2026-10-11 的 Android 实验 APK，不是电脑安装器。

| 你的电脑 | 下载名称 | 启动入口 |
| --- | --- | --- |
| Windows 10/11 64 位 | `XiaomiReader-windows-x64-v0.3.1.zip` | 解压后双击 `启动_Windows.bat` 或 `XiaomiReader.exe` |
| macOS Intel | `XiaomiReader-macos-x64-v0.3.1.zip` | 双击 `XiaomiReader.app` |
| macOS Apple Silicon | `XiaomiReader-macos-arm64-v0.3.1.zip` | 双击 `XiaomiReader.app` |
| Linux x86-64 桌面 | `XiaomiReader-linux-x64-v0.3.1.zip` | 终端执行 `bash 启动_Linux.sh` |

这些发布包使用 GitHub Actions 原生系统构建 PyInstaller 可执行程序，**不需要手动安装 Python**。它们不是注册到 Windows“应用和功能”中的 MSI，也不是经 Apple 签名公证的 DMG；应解压后直接使用。Windows SmartScreen 与 macOS Gatekeeper 可能对未签名应用报警。只从仓库 Releases 获取并检查 SHA-256；如系统拒绝，不要关闭系统安全防护来绕过未知来源风险。

## 上手顺序

1. 解压**整个** ZIP。不要只拖出 EXE。
2. 在设备上开启开发者模式和 USB 调试，用线连接阅读器；在设备屏幕上允许这台电脑调试。
3. 打开电脑端程序，点“检查环境 / USB”。如果缺少 ADB，点“下载官方 ADB”；必须先阅读并接受 Google 官方 SDK 条款，下载后会记录哈希。此步需要联网，后续同一电脑可离线操作。
4. 点“查看阅读器”，确认型号、Android 版本和设备序列号。
5. 先“备份旧阅读器”再“验证备份 ZIP”。恢复前还会先为目标设备备份；任何不完整采集将阻止自动安装。
6. “恢复第三方 APK”仅在确认源包与设备兼容、指定准确目标序列号并输入 `INSTALL` 后生效。不会自动恢复 Magisk、LSPosed、电源键挂钩、日历刷新或整机固件。

## 自研 Android APK 软件包

可下载 `EPD106A-first-party-APKs-2026-10-11.zip`，仅包含本仓库此前已发布且 SHA-256 固定的三个实验版自研 APK。它们属于**历史实验版**，不是 2026-10-14 后最新源码构建，不是系统镜像，也不能保证直接覆盖其他签名的应用；不要因为签名冲突就先卸载清数据。安装/激活仍必须阅读 [同机型安全复制手册](SAME_DEVICE_RESTORE.md)，严格核验 EPD106A 固件指纹、Magisk、LSPosed 作用域与救援护栏。

**公开下载包不会包含**：Google ADB/Fastboot、Magisk、LSPosed、NeatReader、多看、厂商 ROM、你的私人书籍/账户、Root 数据和分区备份。它们的许可、合法来源和机器兼容性必须分别处理。公开发布完整系统的“傻瓜克隆包”目前**不可安全实现**。

## 给 AI 调用

发布包内包含 `XiaomiReaderAI`（Windows 为 `.exe`）、`AGENTS.md` 与 `ai/TOOL_MANIFEST.json`；请让具备本机终端及 USB 权限的 AI 首先读取 AGENTS 规范，再运行 `XiaomiReaderAI status`、`XiaomiReaderAI inspect`、`XiaomiReaderAI backup` 等只读命令。安装须另行明确授权和 `--serial`。

## 验收限制

自动 CI 是**电脑程序可构建、启动与模拟设备**测试，不代表新机已经成功复制壁纸日历、Root 挂钩或续航优化。需要两轮验收：哈希/工程回滚，以及实体按键/触控/刷新/耗电产品体验。
