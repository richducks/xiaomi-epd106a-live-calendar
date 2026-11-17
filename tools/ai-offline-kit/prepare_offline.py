#!/usr/bin/env python3
"""用户本地一次性下载官方工具，再生成可脱网携带的跨平台工具仓。

Google Platform-Tools 的下载要求用户自行阅读并接受其 SDK 条款。
这里不替用户接受条款，也不把 Google 二进制打进本次公开分发包。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / 'vendor'
LOCK = ROOT / 'vendor-lock.json'
VERSION = '0.3.0'
# 固定 Python 发行版本，避免未来更新把离线包变成不可重现的随机版本。
PYTHON_VERSION = '3.11.18'
PYTHON_RELEASE = '20261110'
PLATFORMS = {
    'windows-x64': ('windows', 'x86_64-pc-windows-msvc'),
    'macos-arm64': ('darwin', 'aarch64-apple-darwin'),
    'macos-x64': ('darwin', 'x86_64-apple-darwin'),
    'linux-x64': ('linux', 'x86_64-unknown-linux-gnu'),
}
USER_AGENT = 'XiaomiReaderOfflineKit/0.3 (Python urllib)'
MAX_UNPACKED = 2 * (1024 ** 3)


def hash_file(p: Path):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def check_inside_archive(name):
    """Prevent zip-slip/tar-slip, including Windows drive and alternate separators."""
    if not name or '\\' in name or ':' in name or '\x00' in name:
        raise ValueError('压缩包包含非法文件名: ' + repr(name))
    p = PurePosixPath(name)
    if p.is_absolute() or any(x in ('', '.', '..') for x in name.strip('/').split('/')):
        raise ValueError('压缩包存在目录穿越: ' + repr(name))
    return p


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print('复用已存在下载: ', dest)
        return
    tmp = dest.with_name(dest.name + '.part')
    if tmp.exists():
        tmp.unlink()
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/octet-stream'})
    print('下载: ', url)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp, tmp.open('wb') as out:
            shutil.copyfileobj(resp, out, 1024 * 1024)
        if tmp.stat().st_size < 100_000:
            raise RuntimeError('下载文件异常小，可能返回错误页面')
        os.replace(tmp, dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def extract_zip_platform_tools(src, dest):
    if dest.exists():
        raise RuntimeError('目录已经存在，不能覆盖：' + str(dest))
    with zipfile.ZipFile(src) as z:
        infos = z.infolist()
        if not infos or sum(i.file_size for i in infos) > MAX_UNPACKED:
            raise ValueError('ADB 压缩包大小异常')
        seen = set()
        with tempfile.TemporaryDirectory(dir=VENDOR, prefix='.unpack-adb-') as scratch:
            out = Path(scratch)
            for i in infos:
                p = check_inside_archive(i.filename.rstrip('/'))
                if p.parts[0] != 'platform-tools' or p.as_posix() in seen:
                    raise ValueError('ADB 压缩包结构无效或重名')
                seen.add(p.as_posix())
                mode = i.external_attr >> 16
                if stat.S_IFMT(mode) == stat.S_IFLNK:
                    raise ValueError('ADB 压缩包包含符号链接，拒绝')
                target = out.joinpath(*p.parts)
                if i.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(i) as fin, target.open('wb') as fout:
                        shutil.copyfileobj(fin, fout, 1024 * 1024)
                    if i.filename.endswith(('/adb', '/fastboot')):
                        target.chmod(target.stat().st_mode | 0o755)
            if not ((out / 'platform-tools' / 'adb').exists() or (out / 'platform-tools' / 'adb.exe').exists()):
                raise RuntimeError('官方压缩包内没有 adb 可执行文件')
            shutil.move(str(out / 'platform-tools'), str(dest))


def extract_python(src, dest):
    if dest.exists():
        raise RuntimeError('目录已经存在，不能覆盖：' + str(dest))
    with tarfile.open(src, 'r:gz') as tar:
        members = tar.getmembers()
        if not members or sum(m.size for m in members) > MAX_UNPACKED:
            raise ValueError('Python 压缩包大小异常')
        seen = set()
        with tempfile.TemporaryDirectory(dir=VENDOR, prefix='.unpack-python-') as scratch:
            out = Path(scratch)
            for m in members:
                p = check_inside_archive(m.name.rstrip('/'))
                if p.parts[0] != 'python' or p.as_posix() in seen:
                    raise ValueError('Python 压缩包结构无效或重名')
                seen.add(p.as_posix())
                dst = out.joinpath(*p.parts)
                if m.isdir():
                    dst.mkdir(parents=True, exist_ok=True)
                elif m.isfile() or m.issym() or m.islnk():
                    # 将归档中的链接物化成普通文件，不允许从归档创建文件系统链接。
                    inp = tar.extractfile(m)
                    if inp is None:
                        raise ValueError('Python 归档无法解析链接：' + m.name)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    with inp, dst.open('wb') as fout:
                        shutil.copyfileobj(inp, fout, 1024 * 1024)
                    dst.chmod(0o755 if (m.mode & 0o111) else 0o644)
                else:
                    raise ValueError('Python 归档含非常规文件: ' + m.name)
            possible = ['python.exe', 'bin/python3', 'bin/python3.11']
            if not any((out / 'python' / x).is_file() for x in possible):
                raise RuntimeError('Python 运行时压缩包没有解释器')
            shutil.move(str(out / 'python'), str(dest))


_GITHUB_ASSETS = None


def github_asset(name):
    """一次拉取固定 release 的资产列表，缓存所有资产的 SHA-256。"""
    global _GITHUB_ASSETS
    if _GITHUB_ASSETS is None:
        api = 'https://api.github.com/repos/astral-sh/python-build-standalone/releases/tags/' + PYTHON_RELEASE
        req = urllib.request.Request(api, headers={'User-Agent': USER_AGENT, 'Accept': 'application/vnd.github+json'})
        with urllib.request.urlopen(req, timeout=45) as res:
            release = json.load(res)
        assets = list(release.get('assets', []))
        if len(assets) >= 100:  # GitHub release response embeds only a limited first page.
            for page in range(1, 20):
                url = f"https://api.github.com/repos/astral-sh/python-build-standalone/releases/{release['id']}/assets?per_page=100&page={page}"
                req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/vnd.github+json'})
                with urllib.request.urlopen(req, timeout=45) as res:
                    part = json.load(res)
                assets.extend(part)
                if len(part) < 100:
                    break
        _GITHUB_ASSETS = {a['name']: (a.get('browser_download_url'), a.get('digest', '')) for a in assets}
    item = _GITHUB_ASSETS.get(name)
    if not item:
        raise RuntimeError('GitHub Release 未找到此构建: ' + name)
    url, digest = item
    if not isinstance(digest, str) or not digest.startswith('sha256:'):
        raise RuntimeError('GitHub Release 未提供 Python 运行时 SHA-256')
    return url, digest[len('sha256:'):]


def lock_dict():
    if LOCK.exists():
        return json.loads(LOCK.read_text(encoding='utf-8'))
    return {'schema': 1, 'bundle_version': VERSION, 'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
            'targets': {}, 'note': '只为本机私人离线存档；请遵守上游软件许可；Root 目录绝不可公开上传。'}


def files_hashes(base):
    results = {}
    for p in sorted(base.rglob('*')):
        if p.is_file():
            results[p.relative_to(base).as_posix()] = hash_file(p)
    return results


def current_platform():
    system = platform.system().lower()
    arch = platform.machine().lower()
    if system == 'windows':
        return 'windows-x64' if arch in ('amd64', 'x86_64') else None
    if system == 'darwin':
        return 'macos-arm64' if arch in ('arm64', 'aarch64') else 'macos-x64' if arch == 'x86_64' else None
    if system == 'linux':
        return 'linux-x64' if arch in ('x86_64', 'amd64') else None
    return None


def check_target(target, details=False):
    folder = VENDOR / target
    adb = folder / 'platform-tools' / ('adb.exe' if target.startswith('windows') else 'adb')
    runtime = folder / 'python'
    interpreters = [runtime / 'python.exe', runtime / 'bin' / 'python3', runtime / 'bin' / 'python3.11']
    lock = lock_dict().get('targets', {}).get(target, {})
    status = {'target': target, 'adb_present': adb.is_file(),
              'python_present': any(x.is_file() for x in interpreters),
              'lock_present': bool(lock), 'ready': False}
    if status['adb_present'] and status['python_present'] and lock:
        expected = lock.get('files')
        if isinstance(expected, dict) and expected:
            if details:
                actual = files_hashes(folder)
                status['ready'] = actual == expected
                if not status['ready']:
                    status['problem'] = '本地工具文件清单或哈希不一致'
            else:
                status['ready'] = True
    return status


def prepare(targets, allow_google, no_download=False):
    if not allow_google:
        raise RuntimeError('请先阅读 Google Android SDK 许可协议。确认同意后，传入 --accept-google-sdk-license。')
    VENDOR.mkdir(exist_ok=True)
    meta = lock_dict()
    for target in targets:
        typ, triple = PLATFORMS[target]
        print('\n准备目标:', target)
        folder = VENDOR / target
        if folder.exists() and (folder / 'platform-tools').exists() and (folder / 'python').exists():
            if check_target(target, details=True)['ready']:
                print('已存在有效完整离线工具，跳过')
                continue
            raise RuntimeError(f'{target} 已有文件但未通过校验，拒绝静默覆盖；请备份后人工处理')
        folder.mkdir(parents=True, exist_ok=True)
        adb_url = f'https://dl.google.com/android/repository/platform-tools-latest-{typ}.zip'
        adb_archive = VENDOR / 'source-archives' / f'platform-tools-latest-{typ}.zip'
        if not adb_archive.exists() and no_download:
            raise RuntimeError('离线缓存缺少 ' + str(adb_archive))
        if not no_download:
            download(adb_url, adb_archive)
        if not (folder / 'platform-tools').exists():
            extract_zip_platform_tools(adb_archive, folder / 'platform-tools')
        archive_name = f'cpython-{PYTHON_VERSION}+{PYTHON_RELEASE}-{triple}-install_only_stripped.tar.gz'
        py_archive = VENDOR / 'source-archives' / archive_name
        if no_download:
            if not py_archive.exists():
                raise RuntimeError('离线缓存缺少 ' + str(py_archive))
            # 只接受由先前准备器生成的、已经记录哈希的离线缓存。
            previous = [x.get('python_archive_sha256') for x in meta['targets'].values()
                        if x.get('python_upstream', '').endswith('/' + archive_name)]
            if not previous or hash_file(py_archive) not in previous:
                raise RuntimeError('Python 缓存缺少可验证的历史文件锁，不接受未验证的手工归档')
            url = f'https://github.com/astral-sh/python-build-standalone/releases/download/{PYTHON_RELEASE}/{archive_name}'
        else:
            url, expected_digest = github_asset(archive_name)
            if not py_archive.exists():
                download(url, py_archive)
            if hash_file(py_archive) != expected_digest:
                py_archive.unlink(missing_ok=True)
                raise RuntimeError('Python SHA-256 与 GitHub 发布摘要不符，已删除有问题的缓存')
        if not (folder / 'python').exists():
            extract_python(py_archive, folder / 'python')
        meta['targets'][target] = {
            'adb_upstream': adb_url, 'adb_archive_sha256': hash_file(adb_archive),
            'python_upstream': url, 'python_archive_sha256': hash_file(py_archive),
            'files': files_hashes(folder),
            'prepared_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        LOCK.write_text(json.dumps(meta, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        print('完成:', target, '文件数', len(meta['targets'][target]['files']))


def make_pack(outpath, targets):
    from zipfile import ZIP_DEFLATED
    for target in targets:
        state = check_target(target, details=True)
        if not state['ready']:
            raise RuntimeError('缺少预装或校验失败，不生成伪离线包：' + str(state))
    outpath = outpath.resolve()
    if outpath.exists():
        raise RuntimeError('输出 ZIP 已存在，拒绝覆盖：' + str(outpath))
    if ROOT == outpath or ROOT in outpath.parents:
        raise RuntimeError('输出 ZIP 不能保存在要打包的工程目录内')
    with zipfile.ZipFile(outpath, 'w', ZIP_DEFLATED, compresslevel=5, allowZip64=True) as z:
        for p in sorted(ROOT.rglob('*')):
            if not p.is_file() or p.is_symlink():
                continue
            rel = p.relative_to(ROOT)
            if rel.parts[0] in ('reader-backups', 'cache', '__pycache__', '.git', 'source-archives'):
                continue
            if rel.parts[0] == 'vendor':
                if len(rel.parts) < 2 or rel.parts[1] not in targets:
                    continue
            # 不向脱网包附带个人 Root 数据或旧设备备份。
            z.write(p, arcname=(Path('xiaomi-reader-offline') / rel).as_posix())
    print('已创建私人使用离线工具包：', outpath)
    print('请勿公开再发布包含 Google SDK 或设备私人数据的 ZIP。')


def main():
    p = argparse.ArgumentParser(description='离线工具一次性准备；准备时联网，使用时脱网')
    p.add_argument('--targets', nargs='+', choices=sorted(PLATFORMS), help='要预置的电脑平台，默认仅本机')
    p.add_argument('--all', action='store_true', help='同时预置四种常见系统/架构')
    p.add_argument('--accept-google-sdk-license', action='store_true', help='用户已自行阅读并接受 Google Android SDK 条款')
    p.add_argument('--from-cache', action='store_true', help='只用 vendor/source-archives 中事先下载的文件，不联网')
    p.add_argument('--status', action='store_true', help='检查离线文件是否齐全（严格 SHA-256）')
    p.add_argument('--pack', metavar='ZIP', help='完整准备后，输出可携带的私人离线 ZIP 文件')
    args = p.parse_args()
    targets = list(PLATFORMS) if args.all else args.targets or [current_platform()]
    if None in targets:
        raise RuntimeError('本机架构尚无可确认的官方 ADB 发行版，不能假装可运行；选择受支持目标再制作')
    if args.status:
        print(json.dumps([check_target(t, details=True) for t in targets], ensure_ascii=False, indent=2))
        return 0 if all(check_target(t, details=True)['ready'] for t in targets) else 2
    if args.pack:
        make_pack(Path(args.pack), targets)
        return 0
    prepare(targets, args.accept_google_sdk_license, no_download=args.from_cache)
    print(json.dumps([check_target(t, details=True) for t in targets], ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    # Windows pipes and CI runners may default to cp1252. Preserve Chinese JSON/logs.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')

    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, urllib.error.URLError, tarfile.TarError, zipfile.BadZipFile) as e:
        print('准备失败：' + str(e), file=sys.stderr)
        sys.exit(1)
