@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if not exist "pyproject.toml" (
  echo ERROR: Run this installer from the repository's windows directory.
  exit /b 1
)
if "%CONDA_PREFIX%"=="" (
  echo ERROR: Activate calvados-tea-idp-simulator first.
  exit /b 1
)

echo Checking GPU environment before installing CALVADOS and ELP Studio...
python -c "import openmm; assert openmm.version.full_version.startswith('8.2'), 'Expected OpenMM 8.2'; p=openmm.Platform.getPlatformByName('CUDA'); s=openmm.System(); s.addParticle(1.0); s.addParticle(1.0); f=openmm.HarmonicBondForce(); f.addBond(0,1,0.2,100.0); s.addForce(f); i=openmm.VerletIntegrator(0.001); c=openmm.Context(s,i,p); c.setPositions([[0,0,0],[0.3,0,0]]); force=c.getState(getForces=True).getForces(asNumpy=True); print('CUDA force calculation succeeded on',p.getName(),'-',openmm.version.full_version)"
if errorlevel 1 (
  echo.
  echo CUDA did not pass its force test. Nothing has been installed by pip.
  echo Check CUDA versions and the driver before continuing.
  exit /b 1
)

echo.
echo Installing pinned CALVADOS 0.9.1 without its pip dependency resolver...
python -m pip install --no-deps "git+https://github.com/KULL-Centre/CALVADOS.git@df7d12a3428a0151a9c4683e1300e086d67d8fa5"
if errorlevel 1 exit /b 1

echo.
echo Installing local ELP Studio without replacing Conda's CUDA or OpenMM...
python -m pip install --no-deps -e ".[app,analysis]"
if errorlevel 1 exit /b 1

echo.
echo Checking installed modules...
python -c "import openmm,calvados,MDAnalysis,mdtraj,streamlit; assert openmm.version.full_version.startswith('8.2'); print('CALVADOS + ELP Studio imports OK. OpenMM:',openmm.version.full_version)"
if errorlevel 1 exit /b 1

echo.
echo Running local unit tests...
python -m pytest -q
if errorlevel 1 exit /b 1

echo.
echo SUCCESS: ELP Studio is installed with Conda-managed OpenMM 8.2 and CUDA 12.8.
echo To launch: python -m streamlit run app.py
echo To refresh desktop launcher: windows\install_elp_studio.cmd
exit /b 0
