# One installation: CUDA first, CPU fallback

ELP Studio has **one portable setup** for Windows, Linux, and macOS.
No existing Conda environment, local CALVADOS checkout, or fixed disk
paths are required.

## Install

Install Miniforge (or other Conda distribution) and Git first. From a
Conda-enabled terminal:

```bash
git clone https://github.com/jpdols/CALVADOS-TEA-IDP-simulator.git
cd CALVADOS-TEA-IDP-simulator
python install.py
conda activate calvados-tea-idp-simulator
python -m streamlit run app.py
```

The script creates a new environment automatically. On NVIDIA-equipped
computers, it attempts OpenMM 8.2 + CUDA toolkit 11.8; the CUDA force
calculation must succeed for CUDA to be reported as available.
If GPU installation fails, the script removes **only the new environment
it created during that attempt** and installs the same Conda baseline
without CUDA. On computers without NVIDIA hardware, the CPU setup is
chosen directly. A CPU force calculation must pass in either case.

Both configurations install CALVADOS 0.8.0 from the pinned public
upstream Git commit `75711acbf87cc28e00959b8fb38d5132f66709e4`.
The original source environment that informed the pins is not used
as a dependency. ELP Studio uses `pip --no-deps` to preserve the
Conda-managed simulation backend.

## Update and verify

From the cloned repository directory:

```bash
git pull origin main
python install.py --check
python install.py --update
conda activate calvados-tea-idp-simulator
python -m streamlit run app.py
```

Run `--check` to inspect an existing environment and actually evaluate
forces. Use `--update` to reinstall the application from the updated
checkout without changing the OpenMM/CALVADOS versions.
The installer will not overwrite a pre-existing environment automatically.

For diagnostics:

```bash
python install.py --dry-run
python install.py --cpu
python install.py --gpu
```

The last two options select an installation attempt for a **new** environment,
not an existing one. When the CUDA attempt fails, CPU is still installed
automatically. For a machine that already has an ELP Studio environment
named `calvados-tea-idp-simulator`, `--check` first.

## Hardware compatibility

CUDA depends on NVIDIA hardware and its compatible installed driver.
Detecting CUDA libraries is **not** enough; the installer runs a real
OpenMM force calculation to detect PTX/driver failures. A working
CUDA backend on one machine does not imply it will work elsewhere.
CPU fallback does not need an NVIDIA driver.

The reference environment used for these version selections had Windows
Python 3.10.19, CALVADOS 0.8.0, OpenMM 8.2.0, cudatoolkit 11.8,
NumPy 1.26.4, SciPy 1.15.2, MDAnalysis 2.6.1, MDTraj 1.10.3.
The exact cloned binary installation is **not** a prerequisite.

GitHub CI runs unit tests without GPU hardware. An actual short
CALVADOS simulation remains necessary to validate the full workflow
on a new installation. Do not reuse incomplete trajectories/checkpoints.
