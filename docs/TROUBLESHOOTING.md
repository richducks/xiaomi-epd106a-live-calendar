# 已遭遇的失败、诊断证据和安全恢复（不含厂商源码）

本文件记录 EPD106A 动态锁屏从研究到 Beta 发布出现的实际问题，避免后来的人重复危险试验。公开的是第一方分析和修复思路，不包括厂商专有 APK、固件、反编译源码、个人书籍或设备镜像。

| 问题 | 实际原因或证据 | 处置/结论 |
|---|---|---|
| 修改静态 PNG 后仍看到旧壁纸 | 厂商实际由 `PowerManagerService.showSuspendLogo()` 创建系统层 PNG 窗口，并对图片路径做缓存。 | 停止把 PNG 当动态锁屏；改为在 `PhoneWindowManager.powerPress` 处切换 Android 原生日历 Activity。 |
| 常规 Android 壁纸/屏保不随实体电源键显示 | 原厂 POWER 进入 super standby；`Display Power: state=OFF` 后前台应用不可每分钟刷新物理墨水屏。 | 仅在屏幕保持 Awake/ON 时做真分钟刷新；公开承认续航代价。 |
| 早期底层 `EVIOCGRAB` 测试后实体电源键失效 | 抓取 `/dev/input/event1` 阻断原厂电源策略。 | 立即移除独占监听/测试程序，禁止再将 EVIOCGRAB 作为产品方案。 |
| 早期 Frida 注入后按键模拟超时、system_server 重启 | 动态观察 hook 下的 Android system_server 处理存在稳定性问题。 | 停止 Frida 按键试验，恢复系统，改为 LSPosed 小范围受开关控制的专用模块。 |
| 系统锁屏先显示原图再唤醒日历 | 旧方案在 `goToSleep` 和 `showSuspendLogo` 后才启动 Activity，出现短暂静态图。 | 新方案在普通短按原生 goToSleep **之前**切换；模拟键上未见旧图，实体按键仍需长期验收。 |
| Recovery 上传包显示 `footer is wrong`、`Error 21` | 使用了普通 JAR/APK 签名，缺少 Stock Recovery 要求的 OTA 整包签名尾部。 | 从用户自备合法材料使用 AOSP `signapk -w` 整包签名，保持原厂 Recovery 验签，不关闭安全校验。 |
| Recovery 中挂载 /data 成功却报 `Permission denied`、`Status 7` | Recovery SELinux 域无权搜索 `adb_data_file` 标签的 `/data/adb`。 | 不放宽 SELinux/目录权限；Recovery 只写 /cache，独立 Magisk 早期脚本负责禁用相应模块。 |
| 禁用模块的回退能否工作？ | /cache 安全标记读写与 Magisk 禁用无执行代码模拟模块各自通过实机测试。 | 保留独立护栏和救援包构建工具。**真实 bootloop 事故恢复未主动演练，仍为开放问题。** |
| LSPosed 在该 Android 8.1 系统的启动日志有类查找警告 | 日志曾出现 `ClassNotFoundException: android.os.IServiceCallback$Stub`，但实际 system_server 仍显示策略类成功加载，双短按可用。 | 不能仅凭单条警告推断所有功能失败；结合系统 PID、hook 加载日志、真实日历和回退测试。其他机型未知。 |
| 首次 GitHub Actions 构建失败 | 安装 Android SDK 的 Action 调用了废弃的 `sdkmanager tools`；第二次失败是 SDK Manager 不在 PATH。 | 删除不适配的初始化动作，改为从 `ANDROID_HOME/cmdline-tools` 查找已有 SDK Manager；公开 CI 最终绿色。 |
| GitHub Release 下载后安装脚本找不到 APK | 初版 `install.sh` 只查本地 `build/output`。 | Beta2 加入 `dist/eink-calendar.apk` 和 `dist/eink-livecalendar-policy.apk` 优先路径。 |
| 原项目源码与研究备份混杂，无法安全开源 | 工作目录混有约 5GB 原厂镜像、第三方应用、设备日志和用户资料。 | 从 allowlist 全新 Git 仓库只发布第一方源代码/测试/无用户信息的 UI 图片，并扫描禁止文件/密钥模式。 |
| 用户以为网页排版的 PNG 是动态锁屏 | 网页工作台自身导出的永远是静态 PNG，不能替代 Android 原生分钟刷新。 | 显示“网页预览 · 不同步设备”，说明静态排版工具与设备上运行时日历的明确边界。 |
| 低电量显示造成潜在耗尽 | 墨水屏虽静态不耗电，但 Android SoC 为每分钟更新仍保持 Awake。 | 断电时 <30% 不进入时钟；运行中 <=25% 自动退出。需继续量化长期耗电。 |

## 一线排查命令

```bash
adb devices -l
adb shell getprop sys.boot_completed
adb shell getprop persist.epd.liveclock
adb shell dumpsys power | grep -E 'mWakefulness=|Display Power: state='
adb logcat -d -s EinkLivePowerPolicy:I EinkCalendar:I
```

**任何异常首先执行 `bash scripts/disable.sh`**。在系统不能启动时请按 [RECOVERY.md](RECOVERY.md) 使用用户自建、原厂验证通过的 OTA 救援包。不要盲目刷写设备原厂 boot/system/vendor 或更改受保护的 SELinux 文件。
