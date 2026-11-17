#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")" || exit 1
export PYTHONUTF8=1
for candidate in './vendor/linux-x64/python/bin/python3' './vendor/linux-x64/python/bin/python3.11'; do
  if [ -f "$candidate" ]; then
    chmod u+x "$candidate" 2>/dev/null || true
    exec "$candidate" ./reader_clone.py menu
  fi
done
if command -v python3 >/dev/null 2>&1; then
  exec python3 ./reader_clone.py menu
fi
printf '未找到 Python 3，尚未预置离线运行时。先按 README 完成一次工具准备。\n' >&2
exit 1
