#!/usr/bin/env python3
"""Opt-in backup of local project SOURCE on Windows, macOS or Linux.
No device writes; this is separate from Android ADB capture.
"""
import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

EXCLUDE_DIRS = {'.venv', 'venv', 'node_modules', '__pycache__', '.cache', '.tox', 'dist', 'build', '.git', '.svn', '.hg'}
EXCLUDE_NAMES = {'.env', '.env.local', 'id_rsa', 'id_ed25519', 'known_hosts', '.netrc', '.npmrc'}
EXCLUDE_SUFFIXES = {'.pem', '.p12', '.pfx', '.key', '.keystore'}
MAX_FILE = 100 * 1024 * 1024


def collect_units(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    commands = {
        'user_systemd_units.txt': ['systemctl', '--user', 'list-unit-files', '--no-pager'],
        'system_systemd_units.txt': ['systemctl', 'list-unit-files', '--no-pager'],
        'running_user_services.txt': ['systemctl', '--user', 'list-units', '--type=service', '--no-pager'],
    }
    for name, args in commands.items():
        try:
            result = subprocess.run(args, capture_output=True, timeout=20, text=True, errors='replace')
            (out / name).write_text(result.stdout or result.stderr, encoding='utf-8')
        except (OSError, subprocess.TimeoutExpired) as exc:
            (out / name).write_text(str(exc), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='离线备份阅读器开发工程（显式指定源代码目录）')
    parser.add_argument('--project-dir', required=True)
    parser.add_argument('--output', help='默认输出到当前目录下时间戳 ZIP')
    args = parser.parse_args()
    root = Path(args.project_dir).expanduser().resolve()
    if not root.is_dir():
        parser.error('项目目录不存在')
    if root in (Path.home(), Path('/')) or root.parent == root:
        parser.error('禁止对整个 HOME 或根目录打包')
    output = Path(args.output).expanduser().resolve() if args.output else (Path.cwd() / ('reader_project_%s.zip' % dt.datetime.now().strftime('%Y%m%d_%H%M%S'))).resolve()
    if output.exists():
        parser.error('目标文件已存在，禁止覆盖')
    if output == root or root in output.parents:
        parser.error('输出 ZIP 不能放在被打包的工程目录里面，避免自我递归归档')
    if os.name == 'posix':
        os.umask(0o077)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=3, allowZip64=True) as z:
        count = skipped = 0
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not Path(dirpath, d).is_symlink()]
            for name in filenames:
                source = Path(dirpath, name)
                if source.is_symlink() or name in EXCLUDE_NAMES or source.suffix.lower() in EXCLUDE_SUFFIXES or name.startswith('.env.'):
                    skipped += 1
                    continue
                try:
                    if source.stat().st_size > MAX_FILE:
                        skipped += 1
                        continue
                    z.write(source, arcname='project/' + source.relative_to(root).as_posix())
                    count += 1
                except (OSError, PermissionError):
                    skipped += 1
        z.writestr('META/README.txt', f'Project folder name: {root.name}\nFiles: {count}\nSkipped: {skipped}\nNot a reproducible build or full system image. Review for hardcoded secrets before cloud upload.\n')
    print(f'已打包：{output}\n文件：{count}；排除/跳过：{skipped}')
    print('注意：排除缓存、密钥文件以及超过 100 MB 的文件；项目源码内硬编码的敏感信息仍需人工检查。')


if __name__ == '__main__':
    # Windows pipes and CI runners may default to cp1252. Preserve Chinese JSON/logs.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')

    sys.exit(main())
