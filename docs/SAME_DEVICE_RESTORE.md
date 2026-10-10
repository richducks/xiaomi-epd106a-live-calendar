# EPD106A 2026-10-11 同机型复制／恢复操作手册

## 已验证基线

- 设备：EPD106A / virgo-perf1，Android 8.1 (API 27)，墨案固件 `20240424-143400`。
- Root：Magisk 30.7；Zygisk LSPosed v1.9.2 (7024)。
- 第三方：NeatReader 8.1.4、App Manager 4.1.1（可选）。
- 自研：墨水万年历 `org.epd.calendar`、电源键模块 `org.epd.calendar.policy`、NeatReader 双菜单模块 `org.epd.neat.touchzones`。
- 两个开关：`persist.epd.liveclock=1`，`persist.epd.neatzones=1`。
- LSPosed 作用域：`org.epd.calendar.policy` **仅 Android Framework**；`org.epd.neat.touchzones` **仅 NeatReader**。这不是可互换的作用域。

以上是“配置目标”，而不是可跨设备直接刷写的出厂镜像。

## A. 为当前设备建立本地可恢复检查点

在 Ubuntu 连接当前设备，执行 `bash scripts/snapshot-private.sh`。
此脚本默认只**读取** boot/recovery/system/vendor、当前功能参数、已安装包清单和自研 APK；不刷机、不重启、不清数据。需另外私下备份 Root/LSPosed 数据库、NeatReader 登录和个人书籍时，须在有加密存储的自己电脑上**显式选择** `bash scripts/snapshot-private.sh --include-private-data`。
分区镜像及私有资料存放在电脑的 `$HOME/EPD106A-private-backups`，目录权限 0700、文件 0600；**绝不能上传 GitHub 或分享**。因为设备正在运行，私有数据库和阅读进度文件的热备份未必完全一致；需要停用有关进程后再做一致性恢复演练。

已有分区镜像必须与设备 SHA-256 校验一致才能重用。脚本提供 `--reuse DIR`（DIR 下的 `boot.img` / `recovery.img` / `system.img` / `vendor.img`）避免重复传输。恢复所需的原系统/厂商签名、芯片身份、userdata 和账户，不在 GitHub 公布。

**安全边界：** 镜像备份不等于已验证的整机恢复。恢复分区需要厂商适配的 Recovery/烧录流程、完整可用的备份和签名材料。不能直接通过 `dd of=/dev/block` 盲写；本项目刻意不提供无确认的一键写分区操作。用户数据（书籍、账号、NeatReader 登录、阅读进度）应额外用独立的私有备份工具按需备份，不能克隆至公用发行版。

## B. 复制到第二台同型号阅读器

1. 第二台确认 **EPD106A/virgo-perf1**；使用自己**合法取得且与指纹完全一致**的墨案固件完成刷机。型号或固件不同必须停止；勿套用此机器的 FRP、private、metadata、bootloader。
2. 使用该机匹配的 boot 镜像、官方 Magisk 30.7 和 LSPosed v1.9.2 (7024) 获得 Root、Zygisk 与 LSPosed，并预先验证救援路径。Magisk/LSPosed/墨案固件不在本仓库分发。
3. 从合法渠道安装 **NeatReader 8.1.4**。如果需要 App Manager 4.1.1，可单独安装，不影响核心功能。
4. Ubuntu 执行：
   ```bash
   git clone https://github.com/richducks/xiaomi-epd106a-live-calendar.git
   cd xiaomi-epd106a-live-calendar
   bash scripts/provision-clone.sh --check
   bash scripts/provision-clone.sh --install
   ```
   `--install` 仅安装本项目三个 APK 和恢复护栏，并把两个功能关闭，避免安装期间 system_server 崩溃。
5. 在 LSPosed 里设定上述两个**精确作用域**，重启一次，然后执行：
   ```bash
   EPD_SCOPES_CONFIRMED=YES bash scripts/provision-clone.sh --activate
   bash scripts/provision-clone.sh --check
   ```
6. 分别验证电源键动态日历、书籍阅读进度、中央双菜单、左右翻页、Wi-Fi、电量及正常重启。全部通过才可当成“使用配置复制成功”。

完整恢复路径**不保证所有用户数据一模一样**，尤其是登录状态与个人书籍。刷机/Root 不可逆风险，应先有离线回退和救援途径。

## 发行边界

GitHub Release 附带三个**自研** APK 与 sha256 清单；源码、验收、自动安装、断言及恢复手册保存在本仓库。第三方厂商固件、Magisk、LSPosed、NeatReader、其他应用、OTA 签名钥匙、私有分区镜像和用户备份均未打包。若 GitHub 缺少对应附件或 SHA 不一致，部署脚本必须直接失败。
