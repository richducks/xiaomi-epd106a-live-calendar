# EPD106A 实验版：每 10 分钟 RTC 更新（v0.3.0-alpha.2）

**状态：仅针对 virgo-perf1 / 墨案 Android 8.1，主动启用；不要在其他型号上使用。**

## 机制

保留 NeatReader 自动 60 秒进入原生万年历的行为。RTC 实验模式在初次显示日历约 2.5 秒后要求 PowerManager.goToSleep；设备变成 Asleep / Display OFF，墨水屏靠物理特性保持上一帧。基于 AlarmManager RTC_WAKEUP 的 system_server 闹钟按中国时区整 10 分钟边界唤醒（00/10/20/30/40/50），在原日历 Activity 上请求重新绘制当前 HH:mm，然后约 3.5 秒再入睡。**不保持永久唤醒锁，也不触发旧墨案静态壁纸。** 每次更新时间可能因内核、USB、Doze 或厂商特殊屏幕驱动存在延迟。

低电量：未插电且电量低于 30% 不进入定时日历模式，沿用正常原厂休眠；时钟另有 25% 安全保护。退出日历后不会再主动刷新阅读页面；至多可能剩余一次已注册 RTC 中断，会先检查前台是否仍为日历。

## 安装与开启

必须同时升级至本版 `eink-calendar.apk` 与 `eink-livecalendar-policy.apk`。后者必须在 LSPosed 中仅勾选 Android Framework，安装更新并重启后用 LSPosed 模块日志确认实际加载（不能只看 APK 版本），NeatReader scope 不变。

```bash
bash scripts/enable-tenmin.sh
bash scripts/status.sh
```

若时钟当前已经打开，先点退出回到阅读，再等待原始 60 秒自动超时重新进入。开启模式为 `persist.epd.tenmin=1`，测试加速开关 `persist.epd.tenmin.test=0`（此值不可用于日常），原先 `liveclock/autoclock/neatzones` 仍保持功能正常。

只关闭 10 分钟 RTC 实验、回到旧的每分钟常亮日历：

```bash
bash scripts/disable-tenmin.sh
```

**如优先节电，可直接关闭全部自动时钟接管**：
```bash
adb shell 'su -c "resetprop persist.epd.autoclock 0; resetprop persist.epd.tenmin 0; resetprop persist.epd.tenmin.test 0"'
```
退出时钟后，设备恢复厂商标准休眠；物理电源键打开日历仍有效，具体耗电需另测。

## 验收依据及边界

- 实机在临时 60 秒 RTC 测试间隔下：`Asleep`、`Display OFF`、`DisplaySuspendBlocker=false`；14:08:00 RTC Wake；14:08:00.562 日历确实执行 `update()`，显示文本为 14:08；14:08:03 再休眠。
- 关闭测试加速后，系统 `dumpsys alarm` 确认 `RTC_WAKEUP` 精确闹钟按下一中国时区整 10 分钟边界安排；此为用户现在启用的实验配置。
- 上述实机验证连着 USB，电池正在被 USB 供电；**不能凭此计算节电百分比**。必须拔掉 USB，以原厂睡眠、旧常亮动态日历、RTC 10 分钟模式分三组测量各自 6-12 小时电量，统计黑屏时长、RTC 唤醒频率和页面复原。
- 没有外部摄像头定格证明屏幕局部更新完全没有闪烁；虽已验证软件层刷新触发，但整屏 E-Ink 波形取决于厂商驱动。
- 安装前保留 Magisk/LSPosed 救援护栏和旧 APK。实验失败先 `disable-tenmin.sh`，必要时 `disable.sh`，不要刷写分区。

## 诊断

```bash
adb shell dumpsys power | grep -E 'mWakefulness|Display Power'
adb shell dumpsys alarm | grep -A 5 EpdCalendar10MinuteRTC
adb logcat -d -v time | grep -E 'TENMIN_(RTC|REAL)'
```
