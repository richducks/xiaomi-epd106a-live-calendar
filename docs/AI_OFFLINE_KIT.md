# AI 跨平台离线备份与复用工具仓（v0.3）

本仓库同时维护两条**不能相互替代**的路径：

1. **当前 EPD106A 固件专用的日历部署**：[`scripts/provision-clone.sh`](../scripts/provision-clone.sh) + [`docs/SAME_DEVICE_RESTORE.md`](SAME_DEVICE_RESTORE.md)，强制核验设备固件指纹、Root、LSPosed 作用域并设置救援护栏。已有真实部署经验，但不等于通用 ROM 镜像。
2. **Windows/macOS/Linux 通用备份、检查、离线依赖预载与 AI 命令接口**：[`tools/ai-offline-kit/`](../tools/ai-offline-kit/)。用于收集第三方 APK、诊断、Root 配置快照及在**获得用户明确授权后**安装备份 APK。默认不启用任何 Root 服务、不刷系统分区、不恢复私有数据。通用工具的 APK 恢复不能替代本项目针对 EPD106A 的安全部署程序。

## 获取与准备

克隆 GitHub 仓库并进入 `tools/ai-offline-kit`，准备电脑需要 Python 3.9+。事先阅读并接受 [Google Platform-Tools 许可](https://developer.android.com/tools/releases/platform-tools) 后，在联网电脑运行：

```bash
python3 prepare_offline.py --all --accept-google-sdk-license
python3 prepare_offline.py --all --status
python3 prepare_offline.py --all --pack ../xiaomi-reader-offline-FULL.zip
```

Windows 使用 `py -3` 代替 `python3`。只有**每个平台显示 `ready=true`**，并且已成功生成私人 `xiaomi-reader-offline-FULL.zip`，才算完成预载。GitHub **没有上传**官方 ADB、Fastboot、Python 便携二进制，也没有上传用户自己的 APK/分区/书籍/配置备份。`vendor/`、`vendor-lock.json`、`reader-backups/` 应当留在本地，不要推到公开仓库。

## 让 AI 直接调用

在具有本机终端访问权限的 AI 会话中，请 AI 先阅读 [`AGENTS.md`](../tools/ai-offline-kit/AGENTS.md)、[`ai/TOOL_MANIFEST.json`](../tools/ai-offline-kit/ai/TOOL_MANIFEST.json) 和 [`README_先看这里.md`](../tools/ai-offline-kit/README_先看这里.md)。随后从工具目录调用：

```bash
python ai_runner.py status
python ai_runner.py inspect
python ai_runner.py backup --serial <旧设备序列号>
python ai_runner.py verify --bundle <生成的备份.zip>
```

`restore` 仅在用户事先批准、指定唯一目标设备序列号、备份目标设备并阅读差异后使用：

```bash
python ai_runner.py restore --bundle <备份.zip> --serial <新设备序列号> --approve-install
```

恢复动作只安装兼容 APK；不能据此宣称低功耗日历、实体按键、NeatReader 触控、LSPosed 作用域、旧版服务清理已恢复成功。新机应使用本仓库 `scripts/provision-clone.sh` 对专用模块做更严格的固件与作用域检查。

## 安全与验收边界

- **公开仓库只存可公开的源码与说明**。严禁上传 `vendor/`、`reader-backups/`、`root_overlays`、私人书籍、用户分区镜像、App 登录/令牌。
- 不允许 `fastboot flash`、`dd` 刷分区、`pm clear` 或删除系统应用，除非另行制定独立计划并获得专门确认。本包没有这些自动功能。
- 工程验收：Python 3.9+ 基线、SHA-256 校验、型号与 API 检查、备份完成度、恢复失败可报告。产品验收：实机日历、昼夜刷新、NeatReader 中央菜单、翻页、旧服务唯一性、重启及耗电测试。两轮都通过后才可称 GOLDEN。
- 2026-11-17 本地容器使用模拟 ADB 运行 `RUN_READER_E2E=1 python -m unittest discover -s tests -v`，20 项通过。**Windows/macOS 真机、四平台离线依赖完整预下载和新设备系统恢复尚未验证。**

## 本地运行

在 `tools/ai-offline-kit` 内选择 `启动_Windows.bat`、`启动_macOS.command` 或 `bash 启动_Linux.sh`；或直接使用 Python CLI。测试使用：

```bash
RUN_READER_E2E=1 python3 -m unittest discover -s tests -v
```

跨平台 CI 只验证程序模拟逻辑，不会假装代表 USB/Root/Recovery 实机验收。
