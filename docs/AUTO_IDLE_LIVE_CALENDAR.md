## 2026-10-11 自动息屏与动态日历（EPD106A / Android 8.1）

在原固件中，实体电源键短按会经 `PhoneWindowManager.powerPress`，现有模块拦截后打开日历；但自动闲置屏幕超时直接调用 `PowerManagerService.goToSleepNoUpdateLocked(long,int,int,int)`，以 reason=2 / flags=0 / uid=1000 进入休眠并显示厂商静态 SuspendLogo。这就是过去“按键有效、自动无效”的根因。

本版在**现有 system_server 模块**中增加了**精确方法签名、原因、flags 与 uid**守卫。仅 `persist.epd.liveclock=1` 且 `persist.epd.autoclock=1` 时，才取消对应超时休眠，异步启动**同一个** `org.epd.calendar.MainActivity`；长按电源、其他系统休眠和屏幕保护路径不变。处理失败、Root/LSPosed 未准备好时，优先保留厂商原生休眠；电池低于 30% 且未充电时也恢复普通图片休眠，避免电池过放。

**v0.2.2 额外处理静态图闪一下：**墨案还会在超时事件后另行调用 `PowerManagerService.showSuspendLogo()`，即使先前的 `goToSleepNoUpdateLocked` 已被取消，它仍可能短暂创建显示上一张静态壁纸的顶层 Window。仅在已经获准的**当前自动超时转换后的 2500 毫秒内**，阻止这一个 OEM 绘图方法执行；不覆盖普通电源操作、未启用自动日历或低电量时的静态休眠。源方法和时间窗均是 EPD106A 的厂家定制实现。实机日志应出现 `AUTO_TIMEOUT_VENDOR_SUSPEND_LOGO_SKIPPED`。该日志证明软件未创建静态窗口，不等于硬件绝不会发生墨水屏刷新闪烁。

同时已将设备 `/data/mogu/336369004.png` 中此前测试使用的**静态日历截图**移除并恢复测试前备份的原始静态壁纸（SHA-256 已校验），保证低电量正常休眠有安全回退图片。临时 `/sdcard/__autoclock*.png` 和 `/sdcard/__neat*.png` 测试截图已清理；未删除个人照片、书籍及原始壁纸备份。

**这不是低功耗真休眠。** 动态时钟需要显示层处于 ON 状态才能每分钟更新，因此该模式比静态墨案待机壁纸耗电。日历本身另设 25% 电量保护。实际续航应观察，不能声称持续动态显示与断电待机等耗电。

启用（务必先安装新版 `eink-livecalendar-policy.apk`，在 LSPosed 中只赋予 Android Framework 作用域并重启）：

```bash
bash scripts/enable.sh
bash scripts/status.sh
```

想保留实体按键日历、**单独停用自动超时**：

```bash
adb shell 'su -c "resetprop persist.epd.autoclock 0"'
```

要退出全部日历接管恢复原生休眠：

```bash
bash scripts/disable.sh
```

验收：阅读页闲置超过系统屏幕超时时间后应出现实时日历，`dumpsys power` 应为 Awake；随后跨整分钟确认 HH:mm 改变；短按实体电源或点按日历应回到原阅读任务。为了加速单次验收，可以暂改 `settings put system screen_off_timeout 12000`，**测试完必须还原原值**。禁用自动功能应回到厂商静态屏保（可能因固件省电策略延迟几秒）。

恢复方案文档中的版本钩子与 GitHub Release 文件必须一致，不能把旧版系统模块与新版自动休眠功能混用。
