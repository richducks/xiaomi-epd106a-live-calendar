# Recovery 低风险回退说明

**启动 Android 之前必须安装独立护栏**：`recovery/00-eink-livecalendar-recovery-guard.sh` 放入 `/data/adb/post-fs-data.d/`，root:root，0700。它比 LSPosed 更早执行，且不依赖系统进程。脚本仅在 `/cache/eink-calendar-rescue.disable` 含 `DISABLE_EINK_CALENDAR_V1` 时工作，禁止无条件运行删除命令。

## 普通 Android 故障

在 Ubuntu 输入 `bash scripts/disable.sh` 关闭开关；需要时 `adb shell su -c 'touch /data/adb/modules/zygisk_lsposed/disable'` 然后重启。先确认别的 LSPosed 模块是否依赖它。

## Android 启动失败

1. 用实体按键进入设备官方 Recovery，不要选择 Wipe data/factory reset。
2. 选择 Apply update from ADB。
3. 从 Ubuntu 发送用用户自己的、Recovery 信任的整包签名密钥生成的救援 ZIP（`tools/build_recovery_ota.py --mode rescue`）。
4. Recovery 将在 /cache 写入精确标记，重启时独立护栏会关闭 `eink-livecalendar` 和 `zygisk_lsposed`（保留用户数据）。
5. 如已经有其他系统问题无法启动，停止继续试错，优先保全书籍/完整备份。

## 真实验证结果（2026-10-10）

- Recovery 信任 AOSP 测试证书的整包 OTA 签名；普通 APK/JAR 方式签名被拒绝。
- Recovery 能挂载 /data，但 SELinux 限制 recovery 域直接访问 /data/adb；因此恢复路径改走 /cache。
- Recovery 向 /cache 写测试标记并读回成功，日志 `RECOVERY_CACHE_PROOF_WRITTEN_AND_VERIFIED` + `Install from ADB complete`。
- Magisk 早期脚本读取 /cache 标记并禁用无代码测试模块成功：`EINK_CALENDAR_RECOVERY_DISABLE_OK`，Android 正常重启。
- 真正让 system_server 崩溃的灾难恢复路径**没有故意制造事故演练**；不能保证在所有故障下成功。

本仓库不含备份的原厂 recovery.img、用户专用 root boot.img、第三方 Recovery update-binary 或个人密钥。
