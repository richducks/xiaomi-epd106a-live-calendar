# EPD106A 每分钟 RTC 深度休眠 + E-ink DU 时间局刷：独立双轮验收

日期：2026-10-14；墨案 V07 / Android 8.1 / Magisk Root / LSPosed

## 修复设计
- 生产属性 persist.epd.clock.interval=1，RTC 闹钟按 60000ms 整分钟触发；未设置时默认 600000ms (10分钟)。
- 仍通过 Android system_server 的 RTC_WAKEUP 唤醒 Activity，修改 HH:mm TextView 后重入真实系统休眠，不常亮。
- 厂商 ViewRootImpl.setRefreshMode(1) DU 局部刷新继续启用。
- 日历/节气仅跨日时重画；电量文字只在数值变化时 setText；RTC 重入去掉强制 clock.invalidate 的双重刷新。
- RTC 模式取消 FLAG_KEEP_SCREEN_ON；分钟 RTC 唤醒后等待 2200ms，请求 goToSleep。10分钟模式继续保留原较长的绘制时间和回滚入口。
- 已部署 App v5 与 LSPosed Module v9，versionName 均 0.3.1。

## 第一轮：工程质量
- 构建：bash build.sh && bash build-xposed.sh 成功，签名 v2/v3 校验通过。
- 回归：python3 -m unittest discover -s tests -p test_power_refresh_routing.py -v，11/11 通过。
- 检查范围：自动息屏+电源键入口相同、真实 RTC 唤醒和休眠、周期配置、分钟唤醒时间、局刷文本幂等、电池低电量保护、电量百分比、原始10分钟兼容。
- 升级前 APK 备份：
  build/backups/org.epd.calendar-before-1minute-20261014.apk
  build/backups/org.epd.calendar.policy-before-1minute-20261014.apk

## 第二轮：设备行为
- 09:23:39 电源键进入万年历，TENMIN_ENTRY route=POWER_KEY，interval=60000；09:23:41 进入真实睡眠，Asleep/OFF。
- 09:24:00.101 RTC 唤醒 → 09:24:00.119 时间文字更新 09:24 → 09:24:02.340 再次睡眠。
- 09:25:00.025 RTC 唤醒 → 09:25:00.097 时间文字更新 09:25 → 09:25:02.233 再次睡眠。
- 09:25:09 dumpsys power: Asleep/OFF，约2.2秒 RTC 唤醒窗口。
- 自动息屏：临时设15秒超时；09:25:57 AUTO_TIMEOUT_CALENDAR_LAUNCHED + TENMIN_ENTRY route=AUTO_TIMEOUT + RTC interval=60000；09:25:59 REAL_SLEEP；退出测试后恢复 60000ms 原超时。
- UI树实测 09:26 和 电量 99%，758x1024 实机截图存于 build/qa-minute-20261014/rtc-minute-calendar.png。
- RTC_CLOCK_NO_KEEP_SCREEN_ON 已实机输出；本轮测试模式 persist.epd.tenmin.test=0。

## 限制与风险
- RTC 每分钟唤醒（而不是十分钟），无法达到十分钟方案相同功耗；优于常亮不能等同于实测续航提升。
- USB 连接下的两分钟样本不是无供电的 24/48h 电池测试。
- 已验证 DU 局刷 API 和只改变时间文字，但尚未在物理屏幕上通过摄像机验证无任何整屏闪烁；e-ink 长时间局刷可能出现残影。
- 在真正深睡时，首次按电源键仅唤醒；再次按键才退出万年历（OEM 行为，未随刷新需求修改）。

## 切换和回滚
- 直接切换 10分钟省电优先：./set-refresh-interval.sh 10
- 返回 1分钟显示优先：./set-refresh-interval.sh 1
- 该持久属性会在下一次调度生效；可退出重新进入万年历以立即切换。
- 完全回滚可用上述两个备份 APK 通过 adb install -r 重新安装，属性设回10，并重启设备。
