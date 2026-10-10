# 墨水历 · EPD106A 动态万年历锁屏

[English](README.en.md) · [安装与卸载](docs/INSTALL.md) · [工程/产品验收](docs/ACCEPTANCE.md) · [恢复机制](docs/RECOVERY.md) · [已遇到的问题](docs/TROUBLESHOOTING.md) · [Root 与版权](docs/ROOT_AND_LICENSES.md)

为小米多看阅读器一代、墨案 EPD106A / Android 8.1（virgo-perf1）开发的**开源、原生、真实分钟更新的动态万年历**。本项目不是静态锁屏 PNG：在正常电量下，短按实体电源键直接切换至原生 Android 日历，显示北京时间 `HH:mm`、公历、农历、月历和节气估算、今日手绘墨圈；再次短按返回原阅读任务。

设备原生界面（实机截屏）：

![原生动态万年历](docs/images/native-calendar.png)

网页版排版工具（独立，不会自动同步设备）：

![网页版工作台](docs/images/web-studio.png)

## 最短安装路径

**先阅读 [安装说明](docs/INSTALL.md)。系统级电源键挂接具有启动风险，请先做好 Recovery 回退准备。**

1. Android 8.1 EPD106A 安装最新版 Magisk 并启用 Zygisk；通过其官方渠道安装兼容的 LSPosed（第三方软件，**本仓库不分发**）。
2. 下载本仓库 Releases 中的 `eink-calendar.apk` 和 `eink-livecalendar-policy.apk`，依次安装。
3. 在 LSPosed 管理器中启用 **墨水万年历 · 电源键模块**（org.epd.calendar.policy），**仅**将范围设为 Android Framework（`system`），重启。
4. 先测试能正常启动，再从 Ubuntu 执行 `scripts/enable.sh` 打开功能；从书中短按电源键、等待 1 分钟确认刷新、再短按确认返回书籍原位置。
5. 随时可运行 `scripts/disable.sh` 关闭挂接逻辑；无法启动时参见 [Recovery 救援](docs/RECOVERY.md)。

```bash
# 方式 A：源码构建
bash build.sh && bash build-xposed.sh
# 方式 B：下载 GitHub Release 两份 APK 至 dist/（无需源码构建）
# 最后都使用同一个安装入口
bash scripts/install.sh
# 必须先在 LSPosed 设好 system 范围并重启
bash scripts/enable.sh
bash scripts/status.sh
# 紧急停止（不会删除书籍）
bash scripts/disable.sh
```

构建需要 Ubuntu、JDK 8+、Android SDK platform android-36 和 build-tools 35.0.0；建议使用项目锁定的 API/构建工具版本。SDK 路径来自 `ANDROID_HOME` 或 `~/Android/Sdk`。

## 工作原理

```text
/dev/input/event1 实体 POWER（内核/系统仍由原厂驱动处理）
 → Android PhoneWindowManager.powerPress(long, boolean, int)
 → LSPosed 极小范围 hook（需用户明确开启）
    → 原生 org.epd.calendar/.MainActivity
      → 使用 Android Handler 每分钟整点更新 + 墨水屏固件 DU 局刷
    → 再次短按通过定向广播退出，恢复上一任务
```

只在普通单击、可交互且用户显式开启时切换，长按及多击保持原厂逻辑。原生日历保持显示层 ON 以实现真实每分钟重绘，**不是深度休眠时仍能刷新时间的 AOD**；耗电高于静态睡眠。未接电且电量低于 30% 时不进入动态日历，日历内低于或等于 25% 时自动退出。这个阈值设定是设备保护，不能代替实际续航测量。

网页工作台 `web/index.html` 只用于排版和静态 PNG/JSON 导出，**不会更改安装在阅读器上的原生 UI**。运行：`cd web && python3 -m http.server 8786 --bind 127.0.0.1`，访问 http://127.0.0.1:8786 。

## 兼容性与限制

- **仅 EPD106A / Android 8.1 实机验证**；不要在其他设备盲目启用 system_server hook。
- 节气使用近似公式，极少数日期可能有一天偏差；农历依赖设备 ICU。
- 第三方 LSPosed、Magisk、厂商系统不是本项目的一部分。
- 自助 Recovery 回退经过“写入 /cache”和“开机禁用空模块”两段真实测试，**未在真实不可启动故障上演练**；不可宣称 100% 可救援。
- 系统分区镜像、官方固件、专有 APK、私人备份、密钥和书籍内容均**未随仓库发布**。
- 如发现异常，优先执行 `scripts/disable.sh`，不要尝试底层按键 EVIOCGRAB。

## 测试和发布

```bash
bash build.sh
bash build-xposed.sh
python3 -m unittest discover -s tests -v
# 可选网页浏览器功能测试：需要 Chrome、Pillow、websockets
# 另开终端: python3 -m http.server 8786 --bind 127.0.0.1 --directory web
python3 web/test_web_ui.py
bash scripts/test-device.sh               # 只读检查
bash scripts/test-device.sh --power-cycle  # 需要人工同意，改变当前页面
```

完整工程/产品验收、测试日志和待办见 [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md)。本仓库第一方代码采用 [Apache-2.0](LICENSE) 协议；商标属于各自所有者，非厂商或第三方项目官方产品。

## NeatReader 多看式触控区域（独立组件）

`bash build-neat-zones.sh` 生成 `build/output/eink-neat-touchzones.apk`。模块仅通过 LSPosed 勾选 Neat Reader 作用域，**切勿勾选系统框架或多看**。在原生书籍页轻点屏幕中央或顶部中间区域，会显示位于页面底部的四按钮菜单：上一页、下一页、更多设置、关闭。左、右区域仍交给 NeatReader 原生翻页。

菜单只在同一个 Activity 视图中常驻并切换显隐，不创建独立 PopupWindow，也不重复加载书籍内容。`更多设置` 会调用 NeatReader 原生菜单，该菜单仍可能自行整屏刷新。默认 `persist.epd.neatfast=0`，可选 DU 局刷模式须单独验证后开启；它不能消除 NeatReader 私有电子书解析/加载转圈。

Android 锁屏日历底部显示通过 `ACTION_BATTERY_CHANGED` 获取的实时 `电量 XX%`。
