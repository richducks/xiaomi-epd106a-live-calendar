# 小米阅读器 EPD106A：电源键万年历 10 分钟刷新修复验收

日期：2026-10-14；设备：墨案 V07 / Android 8.1 / Root / LSPosed

## 缺陷与修复范围
- 自动息屏此前调用 `startTenMinuteCycle()`；实体电源键只打开 MainActivity，未调度 RTC 深睡。造成两种启动方式耗电行为不一致。
- 修复：将 RTC 周期启动放到 `PowerPolicyHook.handleTransition` 统一入口，自动息屏和实体电源键都调用；对已打开万年历的自动超时分支兜底；启动周期增加幂等防重。
- 无变更：万年历排版、农历/节气、电量百分比、NeatReader、原生壁纸、ThumbAppSwitcher；不改电池阈值 30%。

## 第一轮：工程质量验收（结构、构建、回归）
- 编译命令：`bash build-xposed.sh`：通过；APK v8；v2/v3 签名校验通过。
- 回归命令：`python3 -m unittest discover -s tests -p 'test_power_refresh_routing.py' -v`：7/7 通过。
- 检查点：两入口共享 RTC 路由、RTC 幂等、已显示时钟不误退出、低电量回退、RTC_WAKEUP 配置、前台分钟 tick 禁用、显示真实电量百分比。
- 变更前安装 APK 备份：`build/backups/eink-livecalendar-policy-before-20261014.apk`；变更后 APK：`build/output/eink-livecalendar-policy.apk`。
- 设备已安装 v8，重启后生效；配置 `persist.epd.tenmin=1`、`persist.epd.tenmin.test=0`。

## 第二轮：产品质量验收（实际设备行为）
1. 电源键路径（ADB KEYCODE_POWER 模拟 Android 电源键事件）：日志 `OPENED_NATIVE_LIVE_CALENDAR` → `TENMIN_ENTRY route=POWER_KEY` → `TENMIN_RTC_WAKE_SCHEDULED interval=600000` → `TENMIN_REAL_SLEEP_REQUESTED`。设备：`mWakefulness=Asleep`，`Display Power: state=OFF`。**通过**。
2. 万年历界面：UI 树显示 `电量 97%`；758×1024 截图存档；前台日志 `TENMIN_FOREGROUND_MINUTE_TICK_DISABLED`。**通过**。
3. 万年历退出：模拟电源键，日志 `CLOCK_EXIT broadcasting finish` 与 `RESTORED_READING_TASK id=2`，前台恢复原应用。**通过**。
4. 自动息屏回归：屏幕自动超时临时调为 15 秒后出现 `AUTO_TIMEOUT_INTERCEPT` → `AUTO_TIMEOUT_CALENDAR_LAUNCHED` → `TENMIN_ENTRY route=AUTO_TIMEOUT` → `TENMIN_RTC_WAKE_SCHEDULED interval=600000` → `TENMIN_REAL_SLEEP_REQUESTED`；设备返回 `Asleep/OFF`。**通过**。
5. 自动息屏测试后恢复系统原值 `screen_off_timeout=60000`。
6. 修复前 RTC 真实定时周期已有日志证明 08:40→08:50→09:00→09:10 每 10 分钟真实唤醒/重绘/重新休眠；修复后两入口复用同一 RTC 函数。

## 未覆盖与限制
- 上述电源键为 ADB 模拟键事件，非人工按压实体开关的机械闭环测试。
- 未测量电池 24h/48h 消耗；“减少耗电”依据真实休眠状态与更少显示/CPU 唤醒，不宣称具体续航百分比。
- 未在修复后完整守候 10 分钟观察手动入口下一次实际唤醒；仅确认同一 RTC 调度与修复前该机制可工作。
- 保持 `persist.epd.tenmin.test=0`，避免遗留高频测试唤醒。

## 可回滚
重装 `build/backups/eink-livecalendar-policy-before-20261014.apk` 并重启，可回到原策略。重装前请核查所处设备和文件路径。
