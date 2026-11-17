@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if exist "%~dp0XiaomiReader.exe" (
  start "" "%~dp0XiaomiReader.exe"
  exit /b 0
)
set "PYTHONUTF8=1"
where py >nul 2>&1
if not errorlevel 1 (py -3 "%~dp0desktop_gui.py" & goto end)
where python >nul 2>&1
if not errorlevel 1 (python "%~dp0desktop_gui.py" & goto end)
echo Cannot find executable. Please download the Windows ZIP from GitHub Releases.
:end
pause
