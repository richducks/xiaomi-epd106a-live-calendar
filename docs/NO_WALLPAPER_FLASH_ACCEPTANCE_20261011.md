# v0.2.2 EPD106A 自动超时静态截图闪现：独立双轮验收（2026-10-11）

## 实际故障

自研实时日历已经能在超时事件后打开，但墨案系统同时异步调用 `PowerManagerService.showSuspendLogo()`，在日历出现前创建旧静态截图锁屏窗口；已确认旧测试截图被配置在 `/data/mogu/336369004.png`，不是 Android 系统普通 WallpaperService 的静态图片。

## 第一轮：工程质量

- 固件匹配：EPD106A / virgo-perf1 / Android 8.1，使用现有 system_server LSPosed 单作用域。
- 原始 `goToSleepNoUpdateLocked(long,int,int,int)` 超时 guard 保持 reason=2 / flags=0 / uid=1000 与两个属性同时开启；未改动短按电源键和 NeatReader 原生菜单。
- 只针对厂家私有 `showSuspendLogo()` 增设 **2500ms** 受限屏蔽窗。仅已拦截自动超时且模块启用时返回 void；在普通休眠、关闭开关、低电量或故障时不屏蔽。
- 异常和原生睡眠回退均清空时间窗，避免将低电量原生锁屏窗口误关掉。
- 独立恢复护栏存在，变更前策略 APK 已保留在 Ubuntu 本地；代码不写 system/boot/recovery/vendor 分区。
- 34 项 Python 现有及新增回归测试全部通过；APK 签名通过；Java 警告为旧 API/编译引导类路径警告。
- LSPosed 在第一次 APK 更新重启时仍引用旧路径，日志显示加载失败；模块数据库之后已同步至新路径，**第二次重启**确认重新加载 `EPD_POLICY_VENDOR_SUSPEND_LOGO_GUARD_READY`，`sys.boot_completed=1`。

## 第二轮：产品体验

- 初次 12 秒超时测试：2026-10-11 08:35:59.579 超时拦截 → 08:35:59.646 厂商 logo 调用被跳过 → 08:35:59.683 日历启动；Activity 为 `org.epd.calendar/.MainActivity`，电源状态 Awake。
- 原始 **60 秒自动超时** 从 NeatReader **BookReaderActivity** 执行：08:38:27.918 AUTO_TIMEOUT_INTERCEPT → 08:38:27.979 AUTO_TIMEOUT_VENDOR_SUSPEND_LOGO_SKIPPED → 08:38:27.990 AUTO_TIMEOUT_CALENDAR_LAUNCHED。
- 随后点击日历退出，恢复同一 NeatReader `BookReaderActivity` 与任务 t148。
- 息屏设置保持 60000 ms。旧静态截图壁纸从 `/data/mogu/336369004.png` 被 **原先备份的非测试静态壁纸**替代，保留正常低电量原生待机能力。
- 校验原始壁纸 SHA256 = `59a6969f29e441d34b285820760244191cf91c8cd563c349b1d850ff4da5b7ae`，设备当前文件相同；所有 14 张 `/sdcard/__autoclock*.png`、`/sdcard/__neat*.png` 临时截图被删除，Ubuntu 生成的截图壁纸预览已删除。用户书籍和照片未删除。

## 仍然存在的验收边界

不具备外部高速摄像头直接量化整屏刷新频次，系统日志只能证明软件层不会再创建静态 SuspendLogo 窗口；硬件 E-Ink 局部/全屏刷新闪烁仍可能存在。低于 30% 的真实电池耗电回退未做破坏性实测。
