# EPD106A 当前状态还原与新机复刻包：两轮独立验收（2026-10-11）

## 验收对象

- EPD106A / virgo-perf1 / Android 8.1 / build 20240424-143400
- 当前直播环境：Magisk 30.7，Zygisk-LSPosed 1.9.2 (7024)，NeatReader 8.1.4，App Manager 4.1.1。
- 第一方：org.epd.calendar、org.epd.calendar.policy、org.epd.neat.touchzones。
- 开关：persist.epd.liveclock=1；persist.epd.neatzones=1。

## 独立第一轮：工程安全/一致性

1. 同一 USB 设备返回 EPD106A，Android API 27 和精确固件指纹。
2. **已核验当前设备**分区 SHA-256 与已有完整镜像相同：
   - boot: `81b2fb49d83885341393db0a8d1a21794ba194eac28cd4845dcb6172dd526c3c`
   - recovery: `bd9a6afde5c2c265c64681e79153aeaa9452f864a247c13b378b1b97c2119fea`
   - system: `1dde9bf551bb3c3bbc1520e0a4a53dc0c82ff61fa3174a742bd70c2138d83f19`
   - vendor: `a201d14305efd91435fb53f0756a5308230c9e555ccaa92a49a3d5cbd8745a91`
3. Ubuntu `root-prep/checkpoint-EPD106A-20261011` 已建立权限受限的约 3.3 GB 分区镜像副本，文件 SHA-256 校验全部成功（该目录不在公开 Git 仓库）。
4. Python 回归测试 **27/27 通过**，shell 校验通过；三个第一方 APK 本地构建、APK 签名验证成功；发行 SHA-256 清单对应即将发布的确定产物。
5. 部署脚本对不同型号、固件指纹不符和多个 USB 设备实行拒绝策略，不含分区写入。
6. 配置恢复依赖精确 LSPosed 作用域和独立恢复护栏；未自动写入 LSPosed 私有数据库。

## 独立第二轮：产品可用性/复制交付

1. **在当前阅读器上只读验证** `bash scripts/provision-clone.sh --check`，获取匹配机型、版本、已安装应用和两项开启状态，未对当前系统执行重新刷写或重装。
2. 2026-10-11 beta.5 已在同一设备验证 NeatReader 中央双菜单、恢复全屏和左右翻页；本次备份脚本不更改这些行为。
3. 只发布自有源码、部署脚本、校验清单和 3 个第一方 APK；不附带原厂固件、Root 签名镜像、NeatReader、Magisk/LSPosed 或用户数据。
4. 在第二台实体 EPD106A 上的完整刷机→Root→LSPosed 作用域→安装→重启→恢复阅读流程**尚未实测**，因此不得宣称“已在第二台机器完整一键还原”。
5. 灾难模式恢复（实际故意破坏 system_server 后再救援）未做；不能承诺分区故障或任意固件版本 100% 恢复。
6. 已验证的是系统分区与第一方软件的可追溯配置。账号、DRM、个人书籍、阅读位置等属于私有数据，不在 GitHub 发布，需要按本人授权另行备份和恢复。

## 需要在第二台设备完成的最终验收

对照 `docs/SAME_DEVICE_RESTORE.md`，检查首次启动、两次关屏/唤醒与日历分钟跳动、Wi-Fi/电量、双菜单及十次左右翻页、Root 与 LSPosed 作用域，断开 USB 后再重启一次。任何项目失败，保留回退路径，不应宣布同配置复制成功。
