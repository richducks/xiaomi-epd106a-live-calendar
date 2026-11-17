# 版本历史

## v0.3.0（2026-11-16）

- 增加有网电脑一次性离线工具准备器 `prepare_offline.py`，可准备 Windows x64、Mac Intel、Mac Apple Silicon、Linux x64 的 ADB+Python。
- 增加 Python 源码发行物 SHA-256 核验，ADB 官方来源 HTTPS 下载并记录本地散列与文件锁清单。
- 增加 `ai_runner.py` JSON 输出、AI 交接提示、`AGENTS.md`、机读工具声明。
- 启动器优先使用离线仓自带 Python；ADB 优先使用匹配平台的离线工具。
- 保留 v0.1/v0.2 备份格式与型号拒绝策略，刷机、清除数据、Root 回放保持禁止。
- 源码包不包含 Google/第三方运行时二进制：当前构建环境无网络；必须在有网电脑准备生成私人 FULL 包。

## v0.2.0

- Windows / macOS / Linux 共用 Python 核心，菜单与模拟设备集成测试。
