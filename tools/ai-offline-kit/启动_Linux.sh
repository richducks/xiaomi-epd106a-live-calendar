#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -f './XiaomiReader' ]; then
  chmod u+x ./XiaomiReader
  exec ./XiaomiReader
fi
if command -v python3 >/dev/null 2>&1; then
  exec python3 ./desktop_gui.py
fi
printf '请下载 GitHub Releases 的 Linux 软件包。\n' >&2
exit 1
