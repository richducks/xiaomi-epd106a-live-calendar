# AI Agent 工作约束——小米阅读器离线工具仓 v0.3

> AI 可以接管**已授权、具有本机终端访问权限**的电脑上的工具仓。仅在聊天里上传 ZIP 并不能让 AI 自动连接用户 USB 设备；需要 AI 会话具备执行本机命令的能力（例如 Work/Computer Use 或终端代理）。

## 初始工作顺序（必须）

1. 读取本文件、`ai/TOOL_MANIFEST.json`、`ai/操作流程.md` 和 `README_先看这里.md`，确认执行目录为当前工程根目录。
2. 按本机平台选择打包的 Python 解释器（优先 `vendor/<target>/python/...`），然后只执行：`python ai_runner.py status`。
3. 查看 JSON 中 `offline_assets.ready` 和 `reader.return_code`。**`ready=false` 不等于备份已执行；无 ADB 时只能准备环境。**
4. 设备信息使用 `python ai_runner.py inspect`，多台设备必须通过 `--serial` 精确指定，Root 不一定存在。
5. 需要备份时 `python ai_runner.py backup --serial <实际序列号>`，检查 JSON 的 `backup_zip`、`snapshot_complete`、`warnings`，再 `python ai_runner.py verify --bundle <实际ZIP>`。
6. 恢复前先备份**目标阅读器**，确认型号、Android API、实际要安装的应用和可接受的数据兼容风险。必须向用户再次明确确认。没有明确授权，只提供安装计划，不执行。
7. 只有用户批准、且明确目标设备时运行：`python ai_runner.py restore --bundle <实际ZIP> --serial <目标序列号> --approve-install`；随后执行人工产品验收。

## 硬性禁止

- 不得将本包描述为厂商 ROM、镜像、全系统/完整用户数据备份。
- 不得执行 `fastboot flash`、`fastboot erase`、`fastboot oem unlock`、`dd`、`mkfs`、`pm clear`、`pm uninstall`、`rm -rf` 等破坏性命令，除非另立独立的操作方案并获得专门确认；此工具包没有这些功能。
- 绝不自动回放 `root_overlays.tar`、`private_app_data/`、Magisk 服务或覆盖系统分区。
- 不得从 APK 列表推断壁纸、刷新策略、触控体验已经被恢复。需要从真实旧设备源码和服务配置做差异核验。
- 不得静默发送设备备份/私有数据到公开 GitHub、网盘或外部服务。公开仓库仅提交不含密钥的脚本、说明和可公开源码。
- 不得下载和执行随机论坛镜像的 adb、刷机包、Root 工具。

## 状态、故障与交付约定

- `ai_runner.py` 对 stdout 输出 JSON，并返回与操作结果一致的进程退出码；错误不能伪装成成功。
- 如备份清单 `snapshot_complete=false`，标记为**部分备份**；可以校验归档文件，但不能等同完整克隆。
- 如 `offline_assets.ready=false`，必须说明哪些工具尚未下载/校验；不要假装已离线可用。
- 按“两轮验收”：第一轮工程完整性（哈希、恢复约束、日志）；第二轮产品体验（日历、省电、触控、多看导航、旧服务唯一性）。两轮独立通过方可称 `GOLDEN`。
- 归档所有操作记录，不保留或输出任何密码和 Root 隐私数据。
