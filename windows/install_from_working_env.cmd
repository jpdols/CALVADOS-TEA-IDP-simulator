@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
set "DEST=calvados-tea-idp-simulator"
set "SOURCE=E:\conda_envs\mep-calvados"

if not exist "%SOURCE%\python.exe" (
  echo ERROR: The proven working environment was not found at "%SOURCE%".
  echo Find it with: conda env list
  exit /b 1
)

if not exist "pyproject.toml" (
  echo ERROR: Run this script from the cloned repository's windows directory.
  exit /b 1
)

call conda env list | findstr /I /C:"%DEST%" >nul
if not errorlevel 1 (
  echo ERROR: An environment named %DEST% already exists.
  echo Do NOT overwrite it automatically. Inspect with: conda env list
  exit /b 1
)

echo Cloning the verified CALVADOS 0.8 / OpenMM 8.2 / CUDA 11.8 environment...
call conda create -y -n "%DEST%" --clone "%SOURCE%"
if errorlevel 1 (
  echo ERROR: Conda clone failed. Existing source environment is unchanged.
  exit /b 1
)

call conda activate "%DEST%"
if errorlevel 1 exit /b 1

echo Verifying Python and GPU before modifying cloned packages...
python -c "import sys,openmm,importlib.metadata as m; assert sys.version_info[:2]==(3,10),sys.version; assert m.version('calvados')=='0.8.0',m.version('calvados'); assert m.version('openmm')=='8.2.0',m.version('openmm'); print('CALVADOS path:',__import__('calvados').__file__)"
if errorlevel 1 exit /b 1
python -m openmm.testInstallation
if errorlevel 1 (
  echo ERROR: OpenMM validation failed after cloning.
  exit /b 1
)

echo Installing ELP Studio WITHOUT resolving or changing its simulation dependencies...
python -m pip install --no-deps --no-build-isolation -e .
if errorlevel 1 exit /b 1

echo Checking ELP Studio import and CALVADOS preparation...
python -c "import calvados,openmm,MDAnalysis,mdtraj,streamlit; from calvados.cfg import Config,Components; import calvados_library_builder.prepare; print('Imports successful, OpenMM:',openmm.version.full_version)"
if errorlevel 1 exit /b 1

echo Checking application tests...
python -m pytest -q
if errorlevel 1 (
  echo WARNING: Tests reported failures. Do not run a production simulation until investigated.
  exit /b 1
)

echo.
echo SUCCESS: %DEST% is installed and the working environment was preserved.
echo Run: conda activate %DEST%
echo Then: python -m streamlit run app.py
echo Optional desktop shortcut: windows\install_elp_studio.cmd
exit /b 0
