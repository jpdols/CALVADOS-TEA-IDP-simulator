@echo off
setlocal
cd /d "%~dp0.."
python install.py %*
if errorlevel 1 (
  echo.
  echo Installation failed. Read the message above; existing Conda environments were not overwritten.
  exit /b 1
)
exit /b 0
