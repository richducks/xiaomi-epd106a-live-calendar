# 10 分钟 RTC 低功耗万年历 alpha.2 — 双轮独立验收

## 工程验收

- EPD106A / virgo-perf1 / Android 8.1（20240424-143400），Boot/LSPosed 救援护栏保留。
- 手动开关 `persist.epd.tenmin`，默认不在第二台设备自动激活；不更改系统固件分区。
- RTC `AlarmManager.setExact(RTC_WAKEUP)`；10 分钟边界，实验验证用 1 分钟临时加速开关，发布时必须置 0。
- 新时间刷新通过既有日历 Activity 的 `onNewIntent`/update，不强制全屏重绘或制造第二个日历。
- 前台不再按分钟执行 `Handler` 刷新任务；真实休眠使用系统服务的 goToSleep；低电量（未充电 <30%）不维持周期。
- 循环中的闹钟严格检查当前前台仍是日历、实验属性仍开启；退出时至多还有下一次一过性的闹钟检查并自动停止。
- Java 构建、APK 签名、自动化静态测试与 Shell 语法由发行前验收确认，全部通过后方发布；源码与 APK SHA256 需对应。

## 产品验收（已执行）
- 14:00:59 显示万年历后进入 `Asleep`、`Display OFF`、`mHoldingDisplaySuspendBlocker=false`；系统 `RTC_WAKEUP` 闹钟成功注册。
- 14:02:00 RTC 唤醒、14:02:03 再次真实休眠。
- 添加 UI 主动刷新后，14:08:00 RTC 唤醒、14:08:00.562 日历打印 `TENMIN_RTC_REFRESH_APPLIED text=14:08`、14:08:03 再次真实休眠，手机日志证明 UI 更新时间。14:09 复验刷新成功。
- 停止测试加速后，14:10:00 RTC 唤醒；14:10:00.508 日历更新时间为 `14:10`；14:10:03 再次真实休眠；下一次精准安排 `14:20:00`，显示 `interval=600000`。
- 手动唤醒时从 Asleep 返回 Awake/Display ON，日历仍显示。原系统超时设置还原为 60000 毫秒。
- 单次退出日历后，墨案 USB/MTP Activity 抢焦点；这次 USB 连接下未独立确认恢复同一个书籍阅读任务（此前稳定版本通过，仍需要脱离 USB 用户实测）。
- 未测拔掉 USB 后的长时间电池实际耗电、电池低于 30% 的真实场景、整屏 E-Ink 波形和 24 小时 RTC 稳定性。不应宣称 10 分钟刷新后“已提升到多少天续航”。

## 回退及第二台

在 Ubuntu 执行 `bash scripts/disable-tenmin.sh` 可立即关闭实验选项。若要恢复原厂深度休眠而不是旧常亮日历，用 `adb shell 'su -c "resetprop persist.epd.autoclock 0; resetprop persist.epd.tenmin 0"'` 并退出日历。第二台设备经相同固件、Root、LSPosed 后安装三份自研 APK，手动运行 `enable-tenmin.sh`，不可在未确认 scope/救援护栏前自动激活。
