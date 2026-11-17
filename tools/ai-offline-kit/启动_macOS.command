#!/bin/zsh
cd "${0:A:h}" || exit 1
if [[ -d ./XiaomiReader.app ]]; then
  open ./XiaomiReader.app
  exit $?
fi
if [[ -f ./XiaomiReader ]]; then
  chmod u+x ./XiaomiReader
  exec ./XiaomiReader
fi
export PYTHONUTF8=1
if command -v python3 >/dev/null 2>&1; then
  exec python3 ./desktop_gui.py
fi
echo '请从 GitHub Releases 下载与你的 Mac 芯片对应的软件包。'
read '?回车退出：'
