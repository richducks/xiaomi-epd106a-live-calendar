# Root 刷机包、第三方软件和开源许可

## 为什么仓库没有附带原厂 boot.img 和可直接刷写的 Magisk boot.img

原始小米/墨案 boot/recovery/system/vendor 镜像、OTA ZIP、厂商 APK、私有驱动、第三方 NeatReader、多看程序、用户书籍和用户私有备份都不是本项目作者拥有的可再分发版权材料；打包到 GitHub 不能通过“重新命名”或“反编译再打包”解决许可问题。本仓库只开放原创代码、诊断流程和**从用户自行取得合法固件生成刷机包的工具/模板**。

Magisk、LSPosed 和 Xposed API 属于第三方项目，应从其官方合法发行渠道安装。若用其代码构建衍生物，必须按相应许可证履行义务；本仓库不含它们的二进制、私有密钥或完整源码。少量本地编译所需的 Xposed **API 声明占位符**没有实现第三方逻辑。

## 自行制作 Root 刷机包（明确存在刷机风险）

**只支持 EPD106A，其他设备禁止使用。** 你需要自己合法取得当前机型的准确 boot 分区镜像；使用 Magisk 官方工具在个人设备上修补，并检验镜像大小、Android boot magic 和真实设备的分区标识。不要直接刷本仓库某个示例 ZIP——本仓库不含镜像。

`python3 tools/build_recovery_ota.py --help` 可从**用户提供**的修补后 boot.img、原机 Recovery 的 update-binary 和自行取得的 AOSP OTA 签名工具/私钥生成签名的个人 Root 恢复包。仅生成文件，不通过 ADB 发送或刷写。传入 Root 镜像需要 `--accept-root-flash-risk`，软件会核验镜像头、大小并打印校验和；这不是越过机型验证和完整备份的替代品。

Recovery 只有在信任 OTA 整包签名密钥时才会接受包。普通 JAR/APK 签名会失败，不能为了“通过”随便关闭验证。若证书不匹配，不应使用该 Recovery ZIP。

## 救援包

`python3 tools/build_recovery_ota.py --mode rescue ...` 用**自行提供**的合法 recovery/update-binary + 签名工具构建救援包，内容仅为 `/cache/eink-calendar-rescue.disable`。真正关闭模块还依赖已安装的 `recovery/00-eink-livecalendar-recovery-guard.sh`。

## 开源许可证与商标

第一方 Java/Python/JS/shell、原生排版、手绘圈算法按本仓库 [Apache-2.0](../LICENSE) 提供。Xiaomi、多看、墨案、Magisk、LSPosed、Android 等名称仅用于兼容性说明，不代表官方认可。字体依赖系统字体，不复制或发布专有字体文件。
