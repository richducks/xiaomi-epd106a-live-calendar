# 架构与边界（Brooks 工程审查）

## 四个职责边界

1. **设备 / 原厂固件**：提供实体 POWER input、PhoneWindowManager、PowerManager、E-ink 显示更新能力；本项目不修改内核/boot/system/vendor，也不独占 /dev/input/event1。
2. **LSPosed 策略模块** `org.epd.calendar.policy`：只挂接系统 UID 下、Android package 的 `PhoneWindowManager.powerPress(long,boolean,int)`，并只在普通短按且显式属性 `persist.epd.liveclock=1` 时切换；长按、多击和禁用状态保留原厂处理。副作用在 worker HandlerThread 中执行。
3. **原生界面 APK** `org.epd.calendar`：显示实际当前时间、月历、农历、估算节气；窗口 DU 模式局部刷新，整分钟定时，电池阈值保护。一次点击退出，广播退出供策略模块调用。
4. **Recovery 安全通路**：Recovery OTA 在 /cache 生成 disable 标志，Magisk `post-fs-data.d` 独立脚本禁用指定的 `eink-livecalendar` / `zygisk_lsposed` 模块。Recovery 不需要直接访问 /data/adb（SELinux 会拒绝）。

网页排版工具完全独立：本地 JavaScript Canvas + localStorage，无后端、数据库、网络 API 或设备直连。导出 PNG **不会变成动态锁屏**。

## 已有已知故障和策略

- 进程重启 / LSPosed 注入不兼容：见 Recovery 救援；不能依赖 system_server 内的钩子自我恢复。
- 手机没电、拔线：<30% 不进入时钟；显示期间 <=25% 自动退出。续航需要长期实测。
- 页面切换竞态 / 系统任务恢复：系统 task id 有效才能前置；如任务已被系统杀死，Android 最近任务/主页面为降级。快速连续双击有边缘竞态，仍需专项复测。
- 页面绘制方式：刷新模式由厂商非公开 API `ViewRootImpl.setRefreshMode(1)` 提供，反射调用失败时退回常规刷新，记录 Logcat 告警。
- 设备异常：使用 `resetprop persist.epd.liveclock 0`，或 Recovery 标记关闭；不在系统进程反复试探 Frida。

## 技术债与后续

- 系统电源管理和墨水屏 DU API 是厂商定制实现，无法保证其他机型可用。
- 节气是估算值，非权威历法；未来可用独立测试过的精准算法替换。
- 当前原生界面不是“深睡中每分钟刷新”的低功耗显示；实现真正 AOD 需厂商驱动/固件支持，不能以 PNG 伪装。
- 仍需 24h/72h 电量测试、实体按键多次循环、长按关机、不同书籍 App 的恢复验证。
