#!/usr/bin/env python3
"""Xiaomi e-reader non-destructive ADB snapshot and guarded app restore.

No partition flash, no automated privileged-overlay replay, no private-data replay.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import platform
import os
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

SCHEMA = 1
VERSION = "0.3.0"
TOOL_DIR = Path(__file__).resolve().parent
# Select adb once at CLI startup. Unit-level functions retain the same API.
ADB_BIN = "adb"
MAX_ZIP_MEMBER_BYTES = 8 * 1024**3
MAX_ZIP_TOTAL_BYTES = 32 * 1024**3
MAX_ZIP_ENTRIES = 100_000
APP_RE = re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+$")
ROOT_PATHS = (
    "data/adb/modules",
    "data/adb/service.d",
    "data/adb/post-fs-data.d",
    "system/etc/init.d",
)
PROPERTIES = (
    "ro.product.model", "ro.product.device", "ro.product.name",
    "ro.build.fingerprint", "ro.build.version.sdk", "ro.build.version.release",
    "ro.boot.verifiedbootstate", "ro.boot.flash.locked",
)
SNAPSHOT_COMMANDS = {
    "properties.txt": ["shell", "getprop"],
    "packages_user.txt": ["shell", "pm", "list", "packages", "-3"],
    "packages_system.txt": ["shell", "pm", "list", "packages", "-s"],
    "settings_system.txt": ["shell", "settings", "list", "system"],
    "settings_secure.txt": ["shell", "settings", "list", "secure"],
    "settings_global.txt": ["shell", "settings", "list", "global"],
    "processes.txt": ["shell", "ps", "-A"],
    "battery.txt": ["shell", "dumpsys", "battery"],
    "power.txt": ["shell", "dumpsys", "power"],
    "deviceidle.txt": ["shell", "dumpsys", "deviceidle"],
    "display.txt": ["shell", "dumpsys", "display"],
    "activity_services.txt": ["shell", "dumpsys", "activity", "services"],
    "storage.txt": ["shell", "df", "-h"],
    "mounts.txt": ["shell", "mount"],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def safe_rel(path: str) -> bool:
    """Portable relative POSIX path; do not trust archive paths or manifests."""
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path or ":" in path:
        return False
    p = PurePosixPath(path)
    return (not p.is_absolute() and not path.startswith("/") and
            not path.endswith("/") and all(segment not in ("", ".", "..")
                                          for segment in path.split("/")))


def find_adb(requested: str | None = None) -> str | None:
    """Supports explicit path, ADB_PATH, bundled platform-tools, then PATH."""
    explicit = requested or os.environ.get("ADB_PATH")
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        return shutil.which(explicit)
    executable = "adb.exe" if os.name == "nt" else "adb"
    host_os = platform.system().lower()
    host_arch = platform.machine().lower()
    if host_os == "windows" and host_arch in ("amd64", "x86_64"):
        target = "windows-x64"
    elif host_os == "darwin" and host_arch in ("arm64", "aarch64"):
        target = "macos-arm64"
    elif host_os == "darwin" and host_arch == "x86_64":
        target = "macos-x64"
    elif host_os == "linux" and host_arch in ("amd64", "x86_64"):
        target = "linux-x64"
    else:
        target = None
    candidates = [TOOL_DIR / "platform-tools" / executable,
                  TOOL_DIR / "tools" / "platform-tools" / executable]
    if target:
        candidates.insert(0, TOOL_DIR / "vendor" / target / "platform-tools" / executable)
    for candidate in candidates:
        if candidate.is_file():
            if os.name == 'posix' and not os.access(candidate, os.X_OK):
                # ZIP made on Windows may lose the executable bit on macOS/Linux.
                try:
                    candidate.chmod(candidate.stat().st_mode | 0o100)
                except OSError:
                    pass
            if os.name == 'nt' or os.access(candidate, os.X_OK):
                return str(candidate.resolve())
    return shutil.which("adb")


def call(argv: list[str], *, data_file: Path | None = None, timeout: int = 120) -> tuple[int, str, str]:
    try:
        if data_file is not None:
            with data_file.open("wb") as out:
                p = subprocess.run(argv, stdout=out, stderr=subprocess.PIPE, timeout=timeout)
            return p.returncode, "", p.stderr.decode("utf-8", "replace")[-2000:]
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")[-2000:]
    except (OSError, subprocess.TimeoutExpired) as ex:
        return 127, "", str(ex)


def adb(serial: str, *argv: str, data_file: Path | None = None, timeout: int = 120):
    return call([ADB_BIN, "-s", serial, *argv], data_file=data_file, timeout=timeout)


def choose_serial(requested: str | None) -> str:
    if not find_adb(ADB_BIN):
        raise RuntimeError("找不到 adb：请安装当前系统的 Android SDK Platform-Tools，或设置 ADB_PATH 指向 adb 可执行文件。")
    code, out, err = call([ADB_BIN, "devices"], timeout=20)
    if code:
        raise RuntimeError("adb devices 失败：" + err)
    devices = []
    blocked = []
    for line in out.splitlines()[1:]:
        vals = line.split()
        if len(vals) >= 2:
            if vals[1] == "device":
                devices.append(vals[0])
            elif vals[1] in ("unauthorized", "offline"):
                blocked.append(line)
    if requested:
        if requested not in devices:
            raise RuntimeError(f"指定设备 {requested} 当前不可用；已连接：{devices}；异常：{blocked}")
        return requested
    if len(devices) != 1:
        raise RuntimeError(f"需要恰好连接一台已授权设备；已连接 {devices}；异常 {blocked}。多设备请用 --serial。")
    return devices[0]


def prop(serial: str, key: str) -> str:
    rc, out, err = adb(serial, "shell", "getprop", key, timeout=20)
    if rc:
        raise RuntimeError(f"获取 {key} 失败：{err}")
    return out.strip()


def fingerprint(serial: str) -> dict[str, str]:
    return {key: prop(serial, key) for key in PROPERTIES}


def list_packages(serial: str) -> list[str]:
    rc, out, err = adb(serial, "shell", "pm", "list", "packages", "-3", timeout=90)
    if rc:
        raise RuntimeError("读取第三方应用列表失败：" + err)
    return sorted({row.removeprefix("package:").strip() for row in out.splitlines()
                   if row.startswith("package:") and APP_RE.fullmatch(row.removeprefix("package:").strip())})


def check_root(serial: str) -> bool:
    rc, out, _ = adb(serial, "shell", "su", "-c", "id", timeout=25)
    return rc == 0 and "uid=0" in out


def root_exists(serial: str, path: str) -> bool:
    cmd = f"test -e /{path} && echo PRESENT"
    rc, out, _ = adb(serial, "shell", "su", "-c", cmd, timeout=20)
    return rc == 0 and "PRESENT" in out


def root_tar(serial: str, outpath: Path, members: list[str], *, timeout=1200) -> tuple[bool, str]:
    if not members:
        return False, "没有适用路径"
    # Paths are internal hardcoded directories or validated Android package identifiers.
    cmd = "tar -C / -cf - " + " ".join(members)
    rc, _, err = adb(serial, "exec-out", "su", "-c", cmd, data_file=outpath, timeout=timeout)
    if rc != 0 or not outpath.exists() or outpath.stat().st_size < 1024:
        outpath.unlink(missing_ok=True)
        return False, f"tar 失败 (rc={rc}): {err}"
    return True, ""


def inventory_files(base: Path) -> list[dict]:
    items = []
    for f in sorted(base.rglob("*")):
        if f.is_file() and f.name != "manifest.json":
            items.append({"path": f.relative_to(base).as_posix(), "size": f.stat().st_size, "sha256": sha256(f)})
    return items


def dump_json(obj: object, path: Path):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def inspect(args):
    serial = choose_serial(args.serial)
    props = fingerprint(serial)
    print(json.dumps({"serial": serial, "device": props, "root_access": check_root(serial),
                      "third_party_app_count": len(list_packages(serial))}, ensure_ascii=False, indent=2))


def backup(args):
    if os.name == 'posix':
        os.umask(0o077)  # Protect APKs, Magisk archives, and optional private data.
    serial = choose_serial(args.serial)
    props = fingerprint(serial)
    if not props.get("ro.product.model") or not props.get("ro.product.device") or not props.get("ro.build.version.sdk"):
        raise RuntimeError("缺少关键设备指纹，拒绝生成无法校验的快照")
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = (Path(args.output) if args.output else Path.cwd() / "reader-backups" / f"reader_{timestamp}").resolve()
    if dest.exists():
        raise RuntimeError(f"目标目录已存在，禁止覆盖：{dest}")
    dest.mkdir(parents=True, mode=0o700)
    try:
        os.chmod(dest, 0o700)
    except OSError:
        pass
    errors: list[str] = []
    root = check_root(serial)
    manifest = {
        "schema_version": SCHEMA, "capture_tool_version": VERSION,
        "capture_host_os": platform.system(), "created_at": dt.datetime.now().astimezone().isoformat(),
        "source_device": props, "source_serial_sha256": hashlib.sha256(serial.encode()).hexdigest(),
        "root_access": root, "capture_mode": "ADB_APP_AND_CONFIG_SNAPSHOT_NOT_ROM_IMAGE",
        "apk_packages": {}, "root_overlays": [], "private_app_data": [],
        "errors": errors, "limitations": [
            "不是分区镜像；不包含官方固件、内核、recovery、分区表、解锁状态。",
            "不自动恢复 Root 模块、系统配置、应用私有数据或用户账号。",
            "壁纸/翻页/刷新逻辑需要验证真实 APK、服务和包名后才能自动部署。",
        ],
    }
    info = dest / "diagnostics"
    info.mkdir()
    print(f"[1/4] 采集只读信息：{dest}")
    for name, command in SNAPSHOT_COMMANDS.items():
        code, out, err = adb(serial, *command, timeout=100)
        (info / name).write_text(out if code == 0 else f"CAPTURE_FAILED {code}: {err}\n", encoding="utf-8")
        if code:
            errors.append(f"diagnostics/{name}: {err}")
    print("[2/4] 备份第三方应用 APK（不读取应用私有数据）")
    packages = list_packages(serial)
    if args.packages != "all":
        allow = set(Path(args.packages).read_text(encoding="utf-8").splitlines())
        allow = {x.strip() for x in allow if APP_RE.fullmatch(x.strip())}
        packages = [x for x in packages if x in allow]
    for idx, package in enumerate(packages, 1):
        rc, raw, err = adb(serial, "shell", "pm", "path", package, timeout=40)
        paths = [line[len("package:"):].strip() for line in raw.splitlines() if line.startswith("package:")]
        if rc or not paths:
            errors.append(f"APK {package}: pm path 失败 {err}")
            continue
        pkg_dir = dest / "apks" / package
        pkg_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for number, src in enumerate(paths):
            # Android 'pm path' returns only paths; defend against unexpected output.
            if not src.startswith(("/data/app/", "/system/app/", "/system/priv-app/", "/product/app/", "/vendor/app/")):
                errors.append(f"APK {package}: 路径拒绝 {src}")
                continue
            dst = pkg_dir / f"{number:02d}_{Path(src).name}"
            code, _, pull_err = adb(serial, "pull", src, str(dst), timeout=420)
            if (code != 0 or not dst.exists() or dst.stat().st_size <= 512) and root:
                # adb shell users cannot always read /data/app; rooted fallback is read-only.
                dst.unlink(missing_ok=True)
                code, _, pull_err = adb(serial, "exec-out", "su", "-c",
                                        "cat " + shlex.quote(src), data_file=dst, timeout=420)
            valid_apk = False
            if code == 0 and dst.exists() and dst.stat().st_size > 512:
                try:
                    with zipfile.ZipFile(dst) as apk_zip:
                        valid_apk = apk_zip.testzip() is None and bool(apk_zip.namelist())
                except (zipfile.BadZipFile, OSError):
                    valid_apk = False
            if valid_apk:
                saved.append(dst.relative_to(dest).as_posix())
            else:
                dst.unlink(missing_ok=True)
                errors.append(f"APK {package}: 拉取失败或 APK 损坏：{pull_err}")
        if saved:
            manifest["apk_packages"][package] = saved
        if idx % 10 == 0 or idx == len(packages):
            print(f"    已检查 {idx}/{len(packages)} 个应用")
    print("[3/4] 归档 Root 改动目录（只读，不修改设备）")
    if root:
        available = [x for x in ROOT_PATHS if root_exists(serial, x)]
        if available:
            root_file = dest / "root_overlays.tar"
            ok, err = root_tar(serial, root_file, available)
            if ok:
                manifest["root_overlays"] = available
            else:
                errors.append("Root 改动归档失败：" + err)
        if args.private_package:
            private_root = dest / "private_app_data"
            private_root.mkdir(exist_ok=True)
            for package in sorted(set(args.private_package)):
                if not APP_RE.fullmatch(package):
                    errors.append(f"私有目录包名格式无效：{package}")
                    continue
                path = f"data/user/0/{package}"
                if not root_exists(serial, path):
                    errors.append(f"私有目录不存在：{path}")
                    continue
                out = private_root / (package + ".tar")
                ok, err = root_tar(serial, out, [path])
                if ok:
                    manifest["private_app_data"].append(package)
                else:
                    errors.append(f"私有数据 {package} 失败：{err}")
    else:
        errors.append("未取得 su Root 权限：未能采集 Magisk 服务/模块等系统级改动")
    print("[4/4] 校验并生成完整性清单")
    manifest["files"] = inventory_files(dest)
    manifest["apk_requested_count"] = len(packages)
    manifest["apk_saved_count"] = len(manifest["apk_packages"])
    manifest["snapshot_complete"] = len(errors) == 0
    dump_json(manifest, dest / "manifest.json")
    print(f"目录：{dest}")
    print(f"APK {len(manifest['apk_packages'])}/{len(packages)}；Root: {'可用' if root else '不可用'}；告警 {len(errors)}")
    if args.zip:
        zipped = dest.with_suffix(".zip")
        if zipped.exists():
            raise RuntimeError("ZIP 已存在，禁止覆盖：" + str(zipped))
        with zipfile.ZipFile(zipped, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3, allowZip64=True) as z:
            for p in sorted(dest.rglob("*")):
                if p.is_file():
                    z.write(p, arcname=p.relative_to(dest).as_posix())
        print(f"压缩包：{zipped}")
    if errors:
        print("注意：这是不完整备份！详见 manifest.json 的 errors。", file=sys.stderr)
        return 2
    return 0


@contextlib.contextmanager
def bundle_dir(path: Path):
    if path.is_dir():
        if path.is_symlink():
            raise RuntimeError("禁止使用符号链接备份目录")
        yield path
        return
    if not path.is_file() or path.suffix.lower() != ".zip":
        raise RuntimeError("备份必须是一个目录或 ZIP 文件")
    with tempfile.TemporaryDirectory(prefix="reader_snapshot_") as tmp, zipfile.ZipFile(path) as z:
        members = z.infolist()
        if len(members) > MAX_ZIP_ENTRIES:
            raise RuntimeError("ZIP 条目过多")
        seen = set()
        total_bytes = 0
        for m in members:
            name = m.filename
            rel = name[:-1] if name.endswith("/") else name
            if not safe_rel(rel) or rel in seen:
                raise RuntimeError("ZIP 包含不安全或重复路径：" + name)
            seen.add(rel)
            if (m.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError("ZIP 包含符号链接：" + name)
            if m.file_size > MAX_ZIP_MEMBER_BYTES:
                raise RuntimeError("ZIP 单项超出 8GB 安全限制")
            total_bytes += m.file_size
            if total_bytes > MAX_ZIP_TOTAL_BYTES:
                raise RuntimeError("ZIP 累计解压大小超过 32GB 安全限制")
        for m in members:
            target = Path(tmp, m.filename)
            if m.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(m) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)
        yield Path(tmp)


def verify_dir(base: Path) -> tuple[dict, list[str]]:
    p = base / "manifest.json"
    if not p.is_file() or p.is_symlink():
        raise RuntimeError("缺少常规 manifest.json 文件")
    manifest = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA:
        raise RuntimeError("不支持的 manifest 版本")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise RuntimeError("manifest 文件清单损坏")
    problems = []
    tracked = set()
    for item in files:
        if not isinstance(item, dict):
            problems.append("manifest 文件条目格式错误")
            continue
        relative = item.get("path", "")
        if not safe_rel(relative) or relative in tracked:
            problems.append(f"异常文件路径/重复记录: {relative}")
            continue
        tracked.add(relative)
        file = base / relative
        segments = PurePosixPath(relative).parts
        subpaths = [base.joinpath(*segments[:i]) for i in range(1, len(segments) + 1)]
        if any(part.is_symlink() for part in subpaths):
            problems.append(f"包含符号链接: {relative}")
        elif not file.is_file():
            problems.append(f"文件丢失: {relative}")
        elif file.stat().st_size != item.get("size") or sha256(file) != item.get("sha256"):
            problems.append(f"文件不一致: {relative}")
    real = {f.relative_to(base).as_posix() for f in base.rglob("*") if f.is_file() and f.name != "manifest.json"}
    for path in sorted(real - tracked):
        problems.append(f"清单外多余文件: {path}")
    if not manifest.get("snapshot_complete", False):
        problems.append("采集本身存在遗漏/告警（查看 manifest.errors），虽不意味着文件校验失败")
    return manifest, problems


def verify(args):
    with bundle_dir(Path(args.bundle).resolve()) as base:
        manifest, issues = verify_dir(base)
        print(json.dumps({"archive": str(args.bundle), "file_count": len(manifest.get("files", [])),
                          "app_count": manifest.get("apk_saved_count", 0),
                          "snapshot_complete": manifest.get("snapshot_complete"), "issues": issues},
                         ensure_ascii=False, indent=2))
        return 1 if issues else 0


def validate_device(source: dict, target: dict) -> list[str]:
    critical = ("ro.product.model", "ro.product.device", "ro.build.version.sdk")
    return [f"{x}: 来源={source.get(x)!r} 目标={target.get(x)!r}" for x in critical
            if not source.get(x) or source.get(x) != target.get(x)]


def restore(args):
    if not args.install_apks:
        raise RuntimeError("默认禁止更改设备。仅支持 --install-apks 安装 APK；Root/系统分区不能自动恢复。")
    serial = choose_serial(args.serial)
    with bundle_dir(Path(args.bundle).resolve()) as base:
        manifest, issues = verify_dir(base)
        # Incomplete root snapshot need not block APK-only recovery, but corrupt files must.
        corruption = [x for x in issues if not x.startswith("采集本身存在")]
        if corruption:
            raise RuntimeError("完整性验证失败：" + "; ".join(corruption[:5]))
        target = fingerprint(serial)
        mismatch = validate_device(manifest["source_device"], target)
        if mismatch:
            raise RuntimeError("设备/Android API 不匹配，停止部署：" + "; ".join(mismatch))
        packages = manifest.get("apk_packages", {})
        if not isinstance(packages, dict):
            raise RuntimeError("备份中的 APK 包清单格式无效")
        if not packages:
            raise RuntimeError("没有可安装的 APK")
        print(f"即将为设备 {serial} 安装/更新 {len(packages)} 个第三方应用 APK。")
        print("不清除新设备数据，不卸载旧应用，不恢复 Root 服务或私有数据。")
        if not manifest.get("snapshot_complete", False):
            print("警告：来源快照不完整；只能安装已通过哈希校验的 APK。")
        if not args.yes:
            raise RuntimeError("尚未执行。请确认目标设备，并追加 --yes 明确授权安装。")
        failed = []
        for package, paths in sorted(packages.items()):
            if not isinstance(package, str) or not APP_RE.fullmatch(package) or not isinstance(paths, list) or not paths:
                failed.append(str(package) + " APK 清单无效")
                continue
            if any(not safe_rel(x) or not x.startswith("apks/" + package + "/")
                   or not x.endswith(".apk") for x in paths):
                failed.append(package + " 文件路径不安全")
                continue
            apks = [str(base / x) for x in paths]
            if len(apks) == 1:
                cmd = ("install", "-r", apks[0])
            else:
                cmd = ("install-multiple", "-r", *apks)
            rc, stdout, err = adb(serial, *cmd, timeout=600)
            print(f"  {package}: {'OK' if rc == 0 and 'Success' in stdout else 'FAIL'}")
            if rc != 0 or "Success" not in stdout:
                failed.append(package + ": " + (err or stdout)[-300:])
        print(f"安装结束：{len(packages)-len(failed)}/{len(packages)}。请执行验收清单进行人工验收。")
        if failed:
            print("失败：" + " | ".join(failed), file=sys.stderr)
            return 2
    return 0


def doctor(args):
    """Check host tooling without writing to the connected Android device."""
    print(f"小米阅读器跨平台工具 v{VERSION}")
    print(f"主机：{platform.platform()} / Python {platform.python_version()}")
    print(f"工作目录：{TOOL_DIR}")
    print(f"ADB：{ADB_BIN}")
    if not find_adb(ADB_BIN):
        print("ADB 未找到。下载官方 Platform-Tools 后解压到本工具的 platform-tools 文件夹。")
        print("官方地址：https://developer.android.com/tools/releases/platform-tools")
        return 1
    rc, out, err = call([ADB_BIN, "version"], timeout=20)
    print((out or err).strip())
    if rc:
        return 1
    rc, out, err = call([ADB_BIN, "devices", "-l"], timeout=20)
    if rc:
        print("设备查询失败：" + err)
        return 1
    print(out.strip() or "无设备")
    print("提示：未连接设备也可先通过环境诊断；设备备份要求 USB 调试已授权。")
    return 0


def menu(args):
    """One common interactive frontend, called from native launchers."""
    cmds = {
        "1": ("环境检查", lambda: ["doctor"]),
        "2": ("查看阅读器", lambda: ["inspect"]),
        "3": ("备份当前阅读器（目录+ZIP）", lambda: ["backup", "--zip"]),
        "4": ("校验备份文件", lambda: ["verify", input("备份 ZIP 或目录路径：").strip().strip('\"')]),
        "5": ("恢复第三方 APK 到新阅读器", lambda: ["restore", input("备份 ZIP 或目录路径：").strip().strip('\"'), "--install-apks"]),
        "6": ("备份电脑上的开发工程", lambda: ["host-source", input("工程文件夹完整路径：").strip().strip('\"')]),
    }
    while True:
        print("\n" + "=" * 49)
        print("小米阅读器 · Windows / macOS / Linux · v" + VERSION)
        for key, (label, _) in cmds.items():
            print(f" {key}. {label}")
        print(" 0. 退出")
        choice = input("请选择 [0-6]：").strip()
        if choice == "0":
            return 0
        if choice not in cmds:
            print("请输入有效选项。")
            continue
        name, build = cmds[choice]
        params = build()
        if choice in ("4", "5", "6") and not params[1]:
            print("路径不能为空")
            continue
        if choice == "5":
            print("只更新目标阅读器上的第三方 APK，不会恢复 Root/壁纸服务/私有数据。")
            if input("确认目标阅读器正确后，输入 INSTALL 执行：").strip() != "INSTALL":
                print("已取消")
                continue
            params.append("--yes")
        if choice == "6":
            subprocess.run([sys.executable, str(TOOL_DIR / "host_source_backup.py"),
                            "--project-dir", params[1]], check=False)
        else:
            prefix = ["--adb", ADB_BIN] if getattr(args, "adb", None) else []
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), *prefix, *params], check=False)
            print("命令退出码：", result.returncode)
        input("按回车返回菜单...")


def main(argv=None):

    parser = argparse.ArgumentParser(description="小米阅读器跨平台备份/迁移工具（非整机分区镜像）")
    parser.add_argument("--adb", help="自定义 adb 可执行文件位置（也可设置环境变量 ADB_PATH）")
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("doctor", help="诊断 Windows/macOS/Linux 主机环境和 ADB")
    p.set_defaults(run=doctor)
    p = sub.add_parser("menu", help="交互式操作菜单，适合双击使用")
    p.set_defaults(run=menu)
    p = sub.add_parser("inspect", help="只读查看 ADB 设备、机型、Root 状态")
    p.add_argument("--serial")
    p.set_defaults(run=inspect)
    p = sub.add_parser("backup", help="备份第三方 APK、系统快照、Root 配置归档")
    p.add_argument("--serial")
    p.add_argument("--output", help="不存在的输出目录，不能覆盖")
    p.add_argument("--packages", default="all", help="all 或每行一个包名的 UTF-8 白名单文件")
    p.add_argument("--private-package", action="append", default=[], help="明确指定单个应用私有数据归档；仅备份，不自动恢复")
    p.add_argument("--zip", action="store_true", help="在目录旁额外输出 ZIP 便于搬运（需要足够磁盘空间）")
    p.set_defaults(run=backup)
    p = sub.add_parser("verify", help="检查快照的每个文件 SHA-256")
    p.add_argument("bundle")
    p.set_defaults(run=verify)
    p = sub.add_parser("restore", help="按硬件型号与 API 版本约束，安装快照 APK")
    p.add_argument("bundle")
    p.add_argument("--serial")
    p.add_argument("--install-apks", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(run=restore)
    args = parser.parse_args(argv)
    global ADB_BIN
    resolved = find_adb(args.adb)
    ADB_BIN = resolved or args.adb or os.environ.get("ADB_PATH") or "adb"
    try:
        return args.run(args)
    except (RuntimeError, ValueError, json.JSONDecodeError, zipfile.BadZipFile,
            EOFError, KeyboardInterrupt, OSError) as exc:
        print("错误：" + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
