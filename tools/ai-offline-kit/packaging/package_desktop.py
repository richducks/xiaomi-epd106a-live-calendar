#!/usr/bin/env python3
"""Create publicly redistributable binaries-only kit; never vendor Google SDK or user backups."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'windows-x64', 'macos-x64', 'macos-arm64', 'linux-x64'}
INCLUDE = ['AGENTS.md', 'AI_PROMPT_复制给AI.txt', 'README_先看这里.md', 'desktop_gui.py',
           'reader_clone.py', 'ai_runner.py', 'host_source_backup.py', 'prepare_offline.py',
           '启动_Windows.bat', '启动_macOS.command', '启动_Linux.sh',
           'ai/TOOL_MANIFEST.json', 'ai/操作流程.md']
USER_GUIDE = '''小米阅读器 · 零 Python 安装版（v0.3.1）

1. 解压整个 ZIP。不要只取出单独一个 EXE。
2. Windows：双击「启动_Windows.bat」或 XiaomiReader.exe。
   macOS：双击 XiaomiReader.app；若被系统阻止，需核对来源并在系统隐私与安全设置中授权。
   Linux：执行 bash 启动_Linux.sh；需要可用的图形桌面和 USB 权限。
3. 打开图形界面，点击“检查环境 / USB”。
4. 没有 ADB 时点击“下载官方 ADB”，先阅读并明确接受 Google SDK 许可。
5. 在阅读器上启用开发者 USB 调试，电脑连接后确认授权，再点“查看阅读器”。
6. 先备份旧设备并校验 ZIP。恢复前先备份目标设备。
7. 恢复仅限兼容第三方 APK；Root、LSPosed、系统分区、日历壁纸服务不能一键恢复。

对 AI：打开 AGENTS.md，然后执行 XiaomiReaderAI status / inspect / backup ...。
注意 AI 只有在可访问本机 USB/终端时才能调用工具。

本程序无厂商 ROM/Magisk/LSPosed/NeatReader APK/用户数据/谷歌 ADB 二进制。
不承诺整机克隆或零风险安装。Windows 未签名，macOS 未公证，部分设备需额外 USB 驱动。
'''


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()


def write_zip(platform_name: str, dest: Path) -> Path:
    if platform_name not in ALLOWED:
        raise ValueError('unsupported release target')
    dist=ROOT/'dist'
    ext='.exe' if platform_name.startswith('windows') else ''
    exe=dist/f'XiaomiReader{ext}'
    ai=dist/f'XiaomiReaderAI{ext}'
    if not exe.is_file() or not ai.is_file():
        raise RuntimeError(f'PyInstaller binaries missing: {exe}, {ai}')
    for path in (exe,ai):
        if path.stat().st_size<500_000:
            raise RuntimeError('binary suspiciously small: '+str(path))
    out=dest/f'XiaomiReader-{platform_name}-v0.3.1.zip'
    if out.exists():
        raise RuntimeError('refuse overwrite: '+str(out))
    dest.mkdir(parents=True,exist_ok=True)
    prefix=f'XiaomiReader-{platform_name}-v0.3.1/'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.write(exe,prefix+exe.name)
        z.write(ai,prefix+ai.name)
        if platform_name.startswith('macos'):
            app=dist/'XiaomiReader.app'
            if not (app/'Contents'/'MacOS'/'XiaomiReader').is_file():
                raise RuntimeError('macOS .app missing; do not publish a CLI-only Mac bundle')
            for p in sorted(app.rglob('*')):
                if p.is_file():
                    z.write(p,prefix+'XiaomiReader.app/'+p.relative_to(app).as_posix())
        z.writestr(prefix+'安装使用说明.txt',USER_GUIDE)
        for rel in INCLUDE:
            source=ROOT/rel
            if not source.is_file():
                raise RuntimeError('release source file missing: '+rel)
            z.write(source,prefix+rel)
    print(json.dumps({'target':platform_name,'release_zip':str(out),'bytes':out.stat().st_size,
                      'sha256':digest(out)},ensure_ascii=False))
    return out


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--target',required=True,choices=sorted(ALLOWED))
    parser.add_argument('--output',default=str(ROOT/'release-output'))
    args=parser.parse_args()
    write_zip(args.target,Path(args.output).resolve())


if __name__=='__main__':
    main()
