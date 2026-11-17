# 小米阅读器 AI 离线部署工具仓 v0.3

这是 **Windows / macOS / Linux 通用的设备备份、校验、受限 APK 恢复和 AI 操作接口**。基于 v0.2 升级，沿用 v0.1/v0.2 备份格式。

**重要交付状态（2026-11-16）**：工具**源码、操作脚本、AI 工作规范、离线依赖准备器已封装**；但当前生成环境**没有网络出口**，**没有成功下载 Google ADB 和四个平台的 Python 二进制运行时**，本次 ZIP 不是“已经包含全部官方二进制”的完成版离线仓。请先在一台有网络的电脑上执行第 1 步，之后即可把准备好的 ZIP 搬运到没网的电脑。

## 1. 有网电脑上只执行一次：准备四个平台全部组件

前提：准备阶段所在电脑装有 Python 3.9+。该要求只用于**首次制作离线仓**，制作成功后目标电脑可直接使用仓内自带 Python，通常不需要额外安装 Python 或 pip。工具无第三方 Python 库。

在终端进入本工具目录，阅读 Google Android SDK 许可协议：<https://developer.android.com/tools/releases/platform-tools>。

如果你已自行同意许可，执行：

```bash
python3 prepare_offline.py --all --accept-google-sdk-license
python3 prepare_offline.py --all --status
python3 prepare_offline.py --all --pack ../xiaomi-reader-offline-FULL.zip
```

**Windows** 把 `python3` 改为 `py -3`。命令会下载：

| 目标平台 | Google Android Platform-Tools | 便携式 Python |
| --- | --- | --- |
| Windows x64 | Windows ADB/Fastboot/必要 DLL | CPython 3.11.18 x86-64 |
| macOS Intel | macOS ADB/Fastboot | CPython 3.11.18 Intel |
| macOS Apple Silicon | macOS ADB/Fastboot | CPython 3.11.18 ARM64 |
| Linux x64 | Linux ADB/Fastboot | CPython 3.11.18 x86-64 |

Python 分发来自 Astral 的 `python-build-standalone` 固定 `20261110` release；下载时从 GitHub release API 校验官方 `sha256` 摘要。Google SDK ZIP 使用 Google 官方 HTTPS 地址，脚本记录首次获取文件的 SHA-256；**Google 此下载入口不提供可由本工具核实的独立官方签名，哈希用于后续一致性，不等于签名校验。**

一次准备完毕，目录内会产生 `vendor/各平台/platform-tools`、`vendor/各平台/python`、`vendor-lock.json`。`--pack` 校验所有文件后生成含真实运行时的个人离线 ZIP。`--status` 返回每个平台 `ready=true` 才算可以完全脱网搬运。**不要把未经检查的第三方 ZIP 当成官方工具。**

准备下载后仍需考虑目标系统的 USB 驱动、macOS 安全授权、Linux udev 规则，特别是 Windows 设备的驱动不一定能随 ADB 一起解决。Linux ARM64/Windows ARM64 原生运行尚未预置官方兼容 ADB，不能假定通用。

> 由于 Android SDK 的许可条款限制复制/再分发，准备程序只供用户在自己接受许可的机器上下载并保存私人备份；请勿公开上传含 Google SDK 二进制的生成 ZIP。

## 2. 全部组件提前下好后，三平台直接打开

- Windows x64：双击 `启动_Windows.bat`；自动优先使用 `vendor/windows-x64/python/python.exe`。
- macOS：双击 `启动_macOS.command`；自动识别 Intel/Apple Silicon。
- Linux x64：在终端 `bash 启动_Linux.sh`。

如果目标设备已连接且允许 USB 调试，菜单提供：环境检测、设备概况、来源 APK+Root 配置归档、备份哈希校验、受控 APK 安装、主机项目源码归档。

`fastboot` 是 Google Platform-Tools 的附带文件，**本工具绝不会自动刷写、解锁或擦除分区**。

## 3. 把 ZIP 给一个能操作电脑的 AI

AI 需要**有权限访问当前电脑目录和执行命令**的终端/计算机操作工具。单纯在没有电脑控制工具的普通聊天中上传 ZIP，只能让 AI 阅读脚本，**不能让它自动读取 USB 设备或运行 ADB**。

打开 `AI_PROMPT_复制给AI.txt`，将其中的话直接复制给 AI，并指定工具目录；AI 会遵守 `AGENTS.md` 及 `ai/TOOL_MANIFEST.json`。

AI 可稳定调用：

```bash
python ai_runner.py status
python ai_runner.py inspect
python ai_runner.py backup --serial <实际设备序列号>
python ai_runner.py verify --bundle <实际备份.zip>
```

输出始终是 JSON（包括 `ok`、`reader.return_code`、`stdout`、`stderr` 等），便于 AI 处理失败分支。需要恢复时，用户明确授权、备份目标机后才使用：

```bash
python ai_runner.py restore --bundle <实际备份.zip> --serial <准确目标序列号> --approve-install
```

自动化默认**不清数据、不卸载应用、不刷分区、不自动恢复 Magisk/Root 服务和应用私有数据**。新设备上的 APK `install -r` 仍有版本/数据兼容风险，请先备份目标机。

## 4. 真实覆盖范围与 GOLDEN 缺口

可以归档：第三方 APK、系统诊断、Root 服务/模块 tar（有 Root 时）、经明确选择的应用私有数据 tar（**不自动恢复**）、本机源码 ZIP。

尚不能一键还原：壁纸日历的真实 APK/脚本与配置、日夜省电刷新、NeatReader 触控映射、Duokan 导航调整、修改系统底层的 ROM/分区等。要实现 `GOLDEN V1.0`，必须先实际采集并验证旧阅读器正在运行的唯一版本，建立部署顺序和独立回滚流程。**本包不是一键镜像刷机包。**

首次做新阅读器验收时，独立执行两轮：工程质量（sha、匹配型号、APK 结果、回滚）以及产品质量（壁纸、省电、按键/触控、唯一服务）。具体见《功能验收清单.md》。私人备份严禁公开上传 GitHub。

## 5. 开发自测

```bash
RUN_READER_E2E=1 python3 -m unittest discover -s tests -v
python3 prepare_offline.py --all --status
python3 ai_runner.py status
```

最后两项在**尚未下载真实二进制时返回非 0 属正常缺件警告**，不要将其当作离线组件验收通过。真实三平台本机 ADB、Mac Intel/ARM、Windows USB 驱动和 Android 真机安装仍需要实际设备验证。

官方工具页：
- Google Android SDK Platform-Tools：<https://developer.android.com/tools/releases/platform-tools>
- Python Build Standalone：<https://github.com/astral-sh/python-build-standalone/releases/tag/20261110>
