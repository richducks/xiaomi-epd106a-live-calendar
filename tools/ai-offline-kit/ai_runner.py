#!/usr/bin/env python3
"""统一 AI 调用入口: 每次输出一个 JSON 对象，无 shell 拼接，无任意命令执行。"""
from __future__ import annotations
import argparse
import contextlib
import datetime as dt
import io
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import reader_clone
from prepare_offline import check_target, current_platform

ROOT = Path(__file__).resolve().parent


def invoke(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = reader_clone.main(argv)
    return {'return_code': int(code or 0), 'stdout': stdout.getvalue(), 'stderr': stderr.getvalue()}


def execute(args):
    action = args.action
    result = {'tool': 'xiaomi-reader-ai-runner', 'tool_version': '0.3.0',
              'action': action, 'timestamp': dt.datetime.now(dt.timezone.utc).isoformat(),
              'host_os': platform.system(), 'host_arch': platform.machine()}
    if action == 'status':
        target = current_platform()
        result['host_target'] = target
        result['offline_assets'] = check_target(target, details=True) if target else None
        result['supported_targets'] = ['windows-x64', 'macos-arm64', 'macos-x64', 'linux-x64']
        # Doctor 可用 PATH 中的 adb；离线齐全与当前在线可用是两个不同概念。
        result['reader'] = invoke(['doctor'])
    elif action == 'inspect':
        cmd = ['inspect']
        if args.serial:
            cmd.extend(['--serial', args.serial])
        result['reader'] = invoke(cmd)
    elif action == 'backup':
        if args.output:
            out = Path(args.output).expanduser().resolve()
        else:
            out = ROOT / 'reader-backups' / ('reader_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        cmd = ['backup', '--output', str(out), '--zip']
        if args.serial:
            cmd.extend(['--serial', args.serial])
        result['reader'] = invoke(cmd)
        result['backup_directory'] = str(out)
        result['backup_zip'] = str(out.with_suffix('.zip'))
        manifest_path = out / 'manifest.json'
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            result['snapshot_complete'] = bool(manifest.get('snapshot_complete'))
            result['warnings'] = manifest.get('errors', [])
    elif action == 'verify':
        result['reader'] = invoke(['verify', args.bundle])
    elif action == 'source':
        if not args.project_dir:
            result['blocked'] = '必须传入 --project-dir 指定真实源码目录；不允许猜测其他工程。'
            result['reader'] = {'return_code': 3, 'stdout': '', 'stderr': ''}
        else:
            cmd = [sys.executable, str(ROOT / 'host_source_backup.py'), '--project-dir', args.project_dir]
            if args.output:
                cmd.extend(['--output', args.output])
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=1800, cwd=str(ROOT))
            result['reader'] = {'return_code': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr}
    elif action == 'restore':
        if not args.approve_install:
            result['blocked'] = '安装属于设备修改操作，需要用户明确授权并使用 --approve-install。'
            result['reader'] = {'return_code': 3, 'stdout': '', 'stderr': ''}
        elif not args.serial:
            result['blocked'] = '恢复必须指定设备序列号 --serial，防止选错目标设备。'
            result['reader'] = {'return_code': 3, 'stdout': '', 'stderr': ''}
        else:
            result['reader'] = invoke(['restore', args.bundle, '--serial', args.serial, '--install-apks', '--yes'])
    else:
        raise ValueError('不支持的命令')
    result['ok'] = result['reader']['return_code'] == 0
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description='AI 可调用的受限 JSON 接口（不支持刷机/删除/任意 shell）')
    p.add_argument('action', choices=['status', 'inspect', 'backup', 'verify', 'restore', 'source'])
    p.add_argument('--serial', help='adb devices 中的准确序列号')
    p.add_argument('--bundle', help='备份 ZIP / 目录（verify、restore 必选）')
    p.add_argument('--output', help='backup 输出目录或 source 输出 ZIP，必须不存在')
    p.add_argument('--project-dir', help='source 用的真实源码目录')
    p.add_argument('--approve-install', action='store_true', help='用户明确授权后才能安装')
    args = p.parse_args(argv)
    if args.action in ('verify', 'restore') and not args.bundle:
        p.error('verify/restore 必须指定 --bundle')
    try:
        payload = execute(args)
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as e:
        payload = {'tool': 'xiaomi-reader-ai-runner', 'action': args.action, 'ok': False,
                   'error': str(e), 'reader': {'return_code': 1, 'stdout': '', 'stderr': str(e)}}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get('ok') else payload.get('reader', {}).get('return_code', 1)

if __name__ == '__main__':
    # Windows pipes and CI runners may default to cp1252. Preserve Chinese JSON/logs.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')

    sys.exit(main())
