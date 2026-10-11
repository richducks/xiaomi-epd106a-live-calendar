# EPD106A 自动闲置日历独立验收记录 · 2026-10-11

## 第一轮：工程质量（代码、构建、回退）
- Android 8.1 services.vdex 解包检查，`PowerManagerService.goToSleepNoUpdateLocked(long,int,int,int)` 返回 boolean，超时入口为 reason 2 / flags 0 / uid 1000。
- 钩子仅允许 `persist.epd.liveclock=1` 与 `persist.epd.autoclock=1` 双开后处理超时；其他睡眠原因保留原固件行为。
- 电池未知/未插电低于 30% 时保留原生静态息屏；异常保护采用熔断与原生休眠回退。
- 线程切换发生在跳过系统超时之后，`startActivity` 在工作线程完成，不在电源锁中执行。
- NeatReader 的 `KEEP_SCREEN_ON` 仅于 `BookReaderActivity` 且开启自动功能时被暂时清除，`onPause` 恢复原标志。
- 原双菜单和左/右翻页逻辑保持；从系统配置可单独关闭自动超时。模块卸载/停用后原厂屏保不受影响。
- 已备份旧策略 APK，独立恢复护栏存在，固件分区备份的 SHA-256 曾与设备逐一匹配。

## 第二轮：产品质量（真实 EPD106A）
- 在 12 秒临时超时下，从 NeatReader 主页面自动触发日历：`AUTO_TIMEOUT_INTERCEPT` / `AUTO_TIMEOUT_CALENDAR_LAUNCHED`，系统 Awake，截屏为真实动态日历，非 SuspendLogo。
- 在 NeatReader 读书页检测到 `mHoldScreenWindow` 对应阅读 Activity（原因：NeatReader 自己的 KEEP_SCREEN_ON）。升级模块后，`NEAT_ALLOW_IDLE_TIMEOUT_KEEP_ON_CLEARED`，`mLastWakeLockHoldingWindow=null`。
- 使用正常 **60 秒**休眠阈值，从 NeatReader 阅读页静置约 72 秒后，实机恢复为 `org.epd.calendar/.MainActivity`，`mWakefulness=Awake`，截屏显示动态万年历（约 08:24，电量 99%）。
- 手动电源键打开、关闭日历路径仍记录 `CLOCK_EXIT` 和 `RESTORED_READING_TASK`。USB 连电脑时曾有原厂 `UsbMtpAcitivity` 抢焦点；这不是应用崩溃。另以 **NeatReader BookReaderActivity → 12 秒超时 → 日历 → 点击退出日历 → 原 BookReaderActivity（同 task）** 做独立验证，成功返回阅读而非书架。
- 用户原系统超时时间 60000 ms 在缩短测试后恢复为 60000 ms；两个日历开关与 NeatReader 触控开关已启用。
- 未在 30% 以下真实电池状态强行耗电演练；低电量逻辑由静态测试覆盖。暂不承诺真实静态关屏功耗，也不承诺其他固件通用兼容。

## 禁止混淆的概念
此功能实现的是**自动闲置后切换到持续刷新的日历 Activity**，显示硬件仍保持 ON 才能显示动态分钟；与省电的真实熄屏不同。能耗与长时间稳定性需要用户后续实际观察。此修复不替换厂商受版权保护的 PNG/系统镜像。
