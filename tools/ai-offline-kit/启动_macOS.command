#!/bin/zsh
cd "${0:A:h}" || exit 1
export PYTHONUTF8=1
if [[ "$(uname -m)" == 'arm64' ]]; then
  arch='macos-arm64'
else
  arch='macos-x64'
fi
for candidate in "./vendor/$arch/python/bin/python3" "./vendor/$arch/python/bin/python3.11"; do
  if [[ -f "$candidate" ]]; then
    chmod u+x "$candidate" 2>/dev/null || true
    "$candidate" ./reader_clone.py menu
    exit $?
  fi
done
if command -v python3 >/dev/null 2>&1; then
  python3 ./reader_clone.py menu
else
  echo '未找到 Python 3，尚未预置离线运行时；需要先运行 prepare_offline.py。'
fi
echo '按回车退出...'
read answer
