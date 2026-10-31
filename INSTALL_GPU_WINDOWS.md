# Fresh Windows NVIDIA GPU installation (OpenMM 8.2 + CUDA 12.8)

This recipe **creates a separate environment** and does not modify the
working `mep-calvados` environment or the older `calvados-elp-local`
environment. Existing simulation files under `runs/` are also untouched.

## Why these versions?

The old Windows Python 3.10 environment successfully computed forces on
the Quadro P1000 with OpenMM 8.2.0 and `cudatoolkit=11.8`. However, the
**Windows Python 3.11 OpenMM 8.2 package** on conda-forge declares CUDA 12
requirements, so using the exact old toolkit in Python 3.11 is not a
reproducible solution.

The NVIDIA driver 573.71 reports support up to CUDA 12.8, so this recipe
pins `cuda-version=12.8` to avoid the previous 12.9 incompatibility.

Upstream CALVADOS 0.9.1 (pinned revision
`df7d12a3428a0151a9c4683e1300e086d67d8fa5`) requires Python >=3.11
and declares a pip CUDA 12 extra for OpenMM. Installing it normally may
replace the Conda OpenMM installation or download mismatched CUDA packages.
Our `windows/finish_install.cmd` installs CALVADOS and this project using
`pip --no-deps` *after* Conda resolves the scientific dependencies.

**This new combination is a pinned installation candidate, not yet a
verified GPU installation on your machine.** The installer checks CUDA
force calculations before it installs the application.

## Setup from an existing clone (Anaconda Prompt, CMD)

Close any running ELP Studio server. From your existing cloned repository:

```bat
cd /d "E:\Master thesis\CALVADOS-TEA-IDP-simulator"
git pull origin main
conda env create -f environment.yml
conda activate calvados-tea-idp-simulator
python -m openmm.testInstallation
windows\finish_install.cmd
windows\install_elp_studio.cmd
python -m streamlit run app.py
```

If `conda env create` reports an existing environment, do **not** use
`conda env update --prune` blindly: check the environment you are updating.
If the Conda solver reports `UnsatisfiableError`, stop and share its
output. Do not add CUDA 11.8 or CUDA 12.9 to this environment.

The `finish_install.cmd` script performs an OpenMM 8.2 CUDA force
calculation first. A failure means the application installation is not
attempted. On success it installs pinned CALVADOS 0.9.1 and editable ELP
Studio without pip dependency resolution, verifies imports, then runs tests.

The desktop launcher setup stores the selected Python interpreter in a
local JSON file and regenerates the shortcut. Start it from the activated
environment so it chooses `calvados-tea-idp-simulator`.

## First simulation

Prepare a **new**, short ELP Studio experiment (e.g. 50 frames,
1000 steps per frame) and select CUDA. Do not reuse a failed simulation
directory or restart an incomplete DCD as if it were a clean run. Check
the batch's `run.log` and `run_error.log` for any runtime exception.

## If you need the previous environment back

Activate the old working installation:

```bat
conda activate "E:\conda_envs\mep-calvados"
python -m openmm.testInstallation
```

None of the commands above modify that environment.
