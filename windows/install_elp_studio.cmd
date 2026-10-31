@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_desktop_shortcut.ps1" %*
if errorlevel 1 (
  echo.
  echo Setup failed. Verify your environment and the message above.
  pause
  exit /b 1
)
echo.
pause
