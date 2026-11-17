@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
cd /d "%~dp0"
set "PYEXE=%~dp0vendor\windows-x64\python\python.exe"
if exist "%PYEXE%" (
  "%PYEXE%" "%~dp0reader_clone.py" menu
  goto end
)
where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%~dp0reader_clone.py" menu
    goto end
)
where python >nul 2>&1
if not errorlevel 1 (
    python "%~dp0reader_clone.py" menu
    goto end
)
echo [FAIL] No Python runtime found; use Python once to run prepare_offline.py, then build offline ZIP.
:end
echo.
pause
endlocal
