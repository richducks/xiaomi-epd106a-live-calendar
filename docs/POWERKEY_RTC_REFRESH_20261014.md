# EPD106A / Android 8.1：电源键和自动息屏统一 RTC 刷新（2026-10-14）

## 问题和已实现修复

历史 10 分钟休眠周期只从自动息屏进入的 `goToSleepNoUpdateLocked` 路径启动。用户短按电源键进入同一个日历时，只执行打开 Activity，不会启动 `startTenMinuteCycle()`，因而保持前台每分钟刷新，产生不必要的常亮耗电。

本次将周期启动移入 `PowerPolicyHook.handleTransition()`，两入口均调度同一 RTC 闹钟。已打开日历时遇到自动超时也会尝试幂等开启周期；退出时取消周期。`persist.epd.tenmin=1` 为 RTC 模式总开关，`persist.epd.clock.interval` 可选 `1` 或 `10`（默认 10）。未启用 RTC 时仍保持原有常亮每分钟模式，不悄然改变其他设置。

RTC 用 `AlarmManager.setExact(RTC_WAKEUP)` 安排整分钟/整十分钟边界，短时唤醒显示层并启动已有 Activity 更新，之后调用 `goToSleep`；不存在屏幕关闭时无电绘制。`MainActivity` 在 RTC 模式清除 `FLAG_KEEP_SCREEN_ON`，同一时间字符串不重复 `setText`，日期未变不重建月历，RTC 再进入时不强制 `clock.invalidate()`。使用厂商 `ViewRootImpl.setRefreshMode(1)` 请求 DU；这不是保证硬件零全刷的通用 Android API。

## 配置和操作

先备份原 APK，并确保 Magisk/LSPosed 模块启用范围仅 Android Framework，且已有 Recovery 安全回退。必须同时安装从本提交构建的 `eink-calendar` 和 `eink-livecalendar-policy`，重启确认模块真正加载后再配置。

```bash
bash build.sh && bash build-xposed.sh
bash scripts/enable.sh
bash scripts/enable-tenmin.sh
./set-refresh-interval.sh 10   # 默认：更少唤醒，更长电池续航的候选模式
./set-refresh-interval.sh 1    # 每分钟 RTC 唤醒，约 2.2 秒后请求重新休眠
```

配置在下一次 RTC 调度时生效；要立即切换，请先退出当前日历，再重新进入。仅设置间隔属性**不会**自动启用 `persist.epd.tenmin=1`。测试时保持 `persist.epd.tenmin.test=0`，勿在日常使用中残留开发测试模式。

回退至原来常亮时钟：`bash scripts/disable-tenmin.sh`。完全放弃时钟接管：`bash scripts/disable.sh`。当低电量未充电（系统策略阈值约 30%）或 RTC 失败时，优先保留原厂睡眠路径；实机回退应结合系统行为再次验证。

## 双轮独立验收与证据边界

第一轮工程验收要求两份 APK 均可构建、签名有效；Python 回归测试覆盖两条入口、周期幂等、低电量、时间文本按需更新、无常亮锁与 1/10 分钟参数。任何新增问题均不因设备可显示而忽略。

第二轮产品验收需要分别验证电源键与自动息屏，分别使用 1/10 分钟参数，检查日志中实际 RTC 安排和 `mWakefulness=Asleep` / Display OFF，以及跨刷新边界时间正确更新、阅读任务恢复。对真实物理按键、e-ink 闪烁/残影、USB 拔线后的 24–48 小时电池续航需另行检验，不能用 ADB 短测替代。

现有实机记录（取自 2026-10-14 本地验收，不等于对 GitHub 源码再刷机）详见：

- [电源键 10 分钟修复验收](ACCEPTANCE-POWERKEY-TENMIN-20261014.md)
- [每分钟 RTC 刷新验收](ACCEPTANCE-MINUTE-RTC-20261014.md)

**范围限制**：仅 EPD106A / virgo-perf1 / Android 8.1。仓库不分发系统镜像、厂商 APK、私人备份、授权文件或用户图书。本提交仅上传第一方源码、脚本和文档，不自动发布二进制安装包。
