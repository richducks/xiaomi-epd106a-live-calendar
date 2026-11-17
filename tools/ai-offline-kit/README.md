# Xiaomi EPD106A AI Offline Kit v0.3

This is an **AI-operable cross-platform backup and limited APK restore toolkit**. Its entry point is `ai_runner.py` and its agent contract is `AGENTS.md`. Open [中文使用说明](README_先看这里.md) for setup and safety details.

This source-only directory does **not** include pre-downloaded Google ADB/Fastboot, standalone Python, firmware, private device images, Root keys or APK backups. Run `prepare_offline.py` on your own online PC after reading and accepting SDK terms; check `--status` before claiming fully offline deployment. Windows, macOS and Linux launch scripts are supplied.

**Critical distinction:** this tool does not reproduce the EPD106A Android OS or activate custom LSPosed services. For the project's device-specific safe installer use [`scripts/provision-clone.sh`](../../scripts/provision-clone.sh). See [integration instructions](../../docs/AI_OFFLINE_KIT.md).

Run simulated tests:

```bash
python -m unittest discover -s tests -v
```

Real USB/Root multi-OS acceptance remains outstanding. Never push device backups or downloaded third-party binaries to this public repository.
