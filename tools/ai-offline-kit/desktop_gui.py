#!/usr/bin/env python3
"""Xiaomi EPD106A graphical companion for Windows, macOS, and Linux.

Requires no installed Python when built with PyInstaller. Only uses safe existing
reader_clone operations. This is not a ROM flasher and cannot restore Root hooks.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import io
import json
import os
import platform
import sys
import threading
import urllib.error
import webbrowser
from pathlib import Path

import reader_clone
import prepare_offline

VERSION = '0.3.1'
GOOGLE_TERMS = 'https://developer.android.com/tools/releases/platform-tools'


def user_data_dir() -> Path:
    return Path(os.environ.get('XIAOMI_READER_DATA_DIR', str(Path.home() / '.xiaomi-reader'))).expanduser().resolve()


def smoke_test() -> int:
    print(json.dumps({'application': 'XiaomiReader', 'version': VERSION,
                      'os': platform.system(), 'arch': platform.machine(),
                      'runtime': 'bundled' if getattr(sys, 'frozen', False) else 'python',
                      'data_path': str(user_data_dir()),
                      'adb_present': bool(reader_clone.find_adb())}, ensure_ascii=False))
    return 0


def fetch_adb() -> str:
    """Called only AFTER user's explicit SDK terms acceptance in GUI."""
    target = prepare_offline.current_platform()
    if not target:
        raise RuntimeError('目前仅提供 Windows x64、macOS Intel/Apple Silicon 和 Linux x64。')
    typ, _ = prepare_offline.PLATFORMS[target]
    prepare_offline.VENDOR.mkdir(parents=True, exist_ok=True)
    dst = prepare_offline.VENDOR / target / 'platform-tools'
    exe = dst / ('adb.exe' if target.startswith('windows') else 'adb')
    if exe.is_file():
        raise RuntimeError('ADB 已存在，拒绝覆盖现有工具：' + str(exe))
    if dst.exists():
        raise RuntimeError('目标目录已存在且不完整，请先检查：' + str(dst))
    src = prepare_offline.VENDOR / 'source-archives' / f'platform-tools-latest-{typ}.zip'
    url = f'https://dl.google.com/android/repository/platform-tools-latest-{typ}.zip'
    prepare_offline.download(url, src)
    prepare_offline.extract_zip_platform_tools(src, dst)
    if not exe.is_file():
        raise RuntimeError('下载结束但未找到 adb；请勿使用不完整目录。')
    if os.name != 'nt':
        exe.chmod(exe.stat().st_mode | 0o755)
    recorded = {'download_url': url, 'archive_sha256': prepare_offline.hash_file(src),
                'adb_sha256': prepare_offline.hash_file(exe),
                'downloaded_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                'note': 'Only hashes of HTTPS download. No independent Google signature validation.'}
    (dst.parent / 'adb-origin.json').write_text(json.dumps(recorded, indent=2), encoding='utf-8')
    # In-process operations after download use the same validated executable.
    reader_clone.ADB_BIN = str(exe.resolve())
    return f'官方 ADB 已安装到：{exe}\nSHA-256：{recorded["adb_sha256"]}\n该哈希供之后校验一致性，并非官方独立签名。'


def safe_default_backup_dir() -> Path:
    base = Path.home() / 'Documents' / 'XiaomiReaderBackups'
    timestamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    return base / f'reader_{timestamp}'


def call_clone(argv: list[str]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        result = reader_clone.main(argv)
    return int(result or 0), output.getvalue()


def start_ui() -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

    root = tk.Tk()
    root.title('小米墨水屏阅读器 · 备份与复用')
    root.geometry('820x620')
    root.minsize(700, 510)
    view = ttk.Frame(root, padding=18)
    view.pack(fill='both', expand=True)
    ttk.Label(view, text='小米阅读器 · 跨平台备份与复用', font=('Arial', 18, 'bold')).pack(anchor='w')
    ttk.Label(view, text='EPD106A 优先 · 不刷 ROM、不覆盖系统分区 · 自动恢复仅限 APK', foreground='#555').pack(anchor='w', pady=(2, 12))
    toolbar = ttk.Frame(view)
    toolbar.pack(fill='x')
    log = scrolledtext.ScrolledText(view, wrap='word', height=16, font=('Courier', 10))
    log.pack(fill='both', expand=True, pady=(12, 10))
    log.insert('end', '先连接阅读器并在设备上允许 USB 调试；如果电脑尚未安装 ADB，请点击“下载官方 ADB”。\n')
    log.configure(state='disabled')
    status = tk.StringVar(value='就绪：尚未执行设备操作')
    ttk.Label(view, textvariable=status, foreground='#234').pack(anchor='w')
    busy = {'running': False}
    buttons: list[ttk.Button] = []

    def append(message: str):
        log.configure(state='normal')
        log.insert('end', message.rstrip() + '\n\n')
        log.see('end')
        log.configure(state='disabled')

    def finish(title: str, ret: int, output: str):
        append(f'【{title}】退出码 {ret}\n{output}')
        status.set('完成' if ret == 0 else '操作未完全成功，请查看上方日志')
        busy['running'] = False
        for button in buttons:
            button.configure(state='normal')

    def run(title: str, task):
        if busy['running']:
            return
        busy['running'] = True
        status.set(f'执行中：{title}（不要拔掉 USB 线）')
        for button in buttons:
            button.configure(state='disabled')
        def worker():
            try:
                result = task()
                code, message = result if isinstance(result, tuple) else (0, str(result))
            except Exception as exc:
                code, message = 1, f'{type(exc).__name__}: {exc}'
            root.after(0, finish, title, code, message)
        threading.Thread(target=worker, daemon=True).start()

    def do_adb():
        if reader_clone.find_adb():
            messagebox.showinfo('已检测到 ADB', f'当前找到：{reader_clone.find_adb()}。无需重复下载。')
            return
        webbrowser.open(GOOGLE_TERMS)
        agreed = messagebox.askyesno('请先阅读 Google 官方许可',
            '已为你打开 Google Android SDK Platform-Tools 官方页面。\n\n'
            '请阅读其许可条款。只有你本人同意条款，才能从 Google 官方服务器下载 ADB。\n\n'
            '是否已经阅读并同意该许可？')
        if agreed:
            run('下载官方 ADB', fetch_adb)

    def do_inspect():
        run('检查阅读器', lambda: call_clone(['inspect']))

    def do_backup():
        out = safe_default_backup_dir()
        if not messagebox.askyesno('只读备份确认',
                f'备份将从已授权 USB 设备读取第三方 APK、诊断和（若有）Root 配置。\n'
                f'本地保存目录：\n{out}\n\n请不要将备份上传公开 GitHub。是否继续？'):
            return
        run('备份阅读器', lambda: call_clone(['backup', '--output', str(out), '--zip']))

    def do_verify():
        f = filedialog.askopenfilename(title='选择已备份的 ZIP', filetypes=[('ZIP 压缩包', '*.zip')])
        if f:
            run('校验备份', lambda: call_clone(['verify', f]))

    def do_restore():
        f = filedialog.askopenfilename(title='选择来源备份 ZIP', filetypes=[('ZIP 压缩包', '*.zip')])
        if not f:
            return
        # Existing snapshot is checked first; do not call install on invalid bundles.
        rc, message = call_clone(['verify', f])
        append('安装前备份校验：\n' + message)
        if rc:
            messagebox.showerror('安装已阻止', '来源备份校验未通过。请检查完整性或备份状态。')
            return
        try:
            serial = reader_clone.choose_serial(None)
        except RuntimeError as exc:
            messagebox.showerror('设备未就绪', str(exc))
            return
        if not messagebox.askyesno('高风险步骤：更新目标应用',
                f'目标设备：{serial}\n\n'
                '此操作会更新目标机上的第三方 APK，可能影响应用现有数据。\n'
                '不会恢复系统 ROM、Root 服务、日历壁纸配置或应用私有数据。\n\n'
                '下一步将先备份目标设备，备份未完整成功时中止安装。\n\n是否继续？'):
            return
        token = simpledialog.askstring('确认安装', '请输入 INSTALL 确认备份和更新目标设备：', parent=root)
        if token != 'INSTALL':
            return
        backup_dir = safe_default_backup_dir()
        def task():
            code, output = call_clone(['backup', '--serial', serial, '--output', str(backup_dir), '--zip'])
            if code:
                return code, '目标机备份不完整，已停止安装。\n' + output
            code2, output2 = call_clone(['restore', f, '--serial', serial, '--install-apks', '--yes'])
            return code2, '目标机备份：' + str(backup_dir.with_suffix('.zip')) + '\n' + output + '\n' + output2
        run('备份目标设备并安装 APK', task)

    def add(label, callback, row, col):
        button = ttk.Button(toolbar, text=label, command=callback)
        button.grid(row=row, column=col, sticky='ew', padx=3, pady=4, ipady=4)
        buttons.append(button)
    for col in range(3):
        toolbar.columnconfigure(col, weight=1)
    add('① 检查环境 / USB', lambda: run('环境检查', lambda: call_clone(['doctor'])), 0, 0)
    add('② 下载官方 ADB', do_adb, 0, 1)
    add('③ 查看阅读器', do_inspect, 0, 2)
    add('④ 备份旧阅读器', do_backup, 1, 0)
    add('⑤ 验证备份 ZIP', do_verify, 1, 1)
    add('⑥ 恢复第三方 APK', do_restore, 1, 2)
    root.mainloop()
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--self-test' in argv:
        return smoke_test()
    # Freeze mode writes into user-owned directory, not the signed app or unpack folder.
    return start_ui()


if __name__ == '__main__':
    sys.exit(main())
