# Windows GPU install: preserve the known-working CALVADOS stack

## Verified baseline (exported from E:\\conda_envs\\mep-calvados)

- Windows NVIDIA Quadro P1000 / driver 573.71
- Python 3.10.19
- CALVADOS 0.8.0 (editable installation at E:\\Master thesis\\calvados)
- OpenMM 8.2.0 from conda-forge (win-64 build py310hb455a88_3)
- cudatoolkit 11.8.0 from conda-forge
- NumPy 1.26.4; SciPy 1.15.2
- MDAnalysis 2.6.1; MDTraj 1.10.3
- Streamlit 1.58.0, Matplotlib 3.10.8, Pandas 2.2.2
- `python -m openmm.testInstallation` computes forces successfully on CUDA.

CALVADOS 0.9.1 is **not necessary** for the existing application's use of
`calvados.cfg.Config`, `Components`, and the generated `run.py`.
Its dependency metadata requires Python >=3.11 and pip `openmm[cuda12]`;
trying to install it previously pulled incompatible CUDA 12.9 libraries.
We retain 0.8.0 until end-to-end compatibility tests justify an upgrade.

## Recommended: clone existing working environment

**Close Streamlit and Jupyter first.** From Windows Anaconda Prompt:

```bat
cd /d "E:\\Master thesis\\CALVADOS-TEA-IDP-simulator"
git pull origin main
windows\\install_from_working_env.cmd
conda activate calvados-tea-idp-simulator
python -m openmm.testInstallation
python -m streamlit run app.py
```

The script runs `conda create -n calvados-tea-idp-simulator --clone
E:\\conda_envs\\mep-calvados`, validates the CUDA force backend, installs
ELP Studio with `pip --no-deps --no-build-isolation -e .`, checks imports
and runs unit tests. It refuses to overwrite an existing destination.
It **does not change** the original `mep-calvados` environment.

**Editable source caveat:** the cloned CALVADOS installation still refers to
`E:\\Master thesis\\calvados`. This preserves any uncommitted local
changes, but means the environment alone is not independently portable.
A truly standalone installation requires recording that local checkout's
`git rev-parse HEAD` and `git status --short`, plus any local patches.

If an *already existing* `calvados-tea-idp-simulator` environment is
reported, inspect it via `conda env list`. Do not remove an environment
without identifying it and backing up any work. The installer deliberately
does not delete or overwrite anything.

## After a successful install

Run `windows\\install_elp_studio.cmd` from the activated new environment
to refresh the portable desktop shortcut. For first validation, prepare a
new short simulation in ELP Studio and select CUDA. Do not reuse a failed
DCD/checkpoint folder. Compare generated YAML parameters and short-run
outputs to the working CALVADOS reference before serious production runs.

## Fresh-machine fallback

`environment.yml` now specifies the same scientific versions under
Python 3.10 and CUDA 11.8. It is **not** guaranteed to reproduce the exact
Conda binary build on another machine. Prefer an explicit Conda export
of the reference environment for bitwise repeatability. A clean-machine
workflow also needs CALVADOS 0.8.0 installed from an identifiable repository
revision; upstream merge commit
`75711acbf87cc28e00959b8fb38d5132f66709e4` corresponds to its 0.8.0
release, but may differ from the user's editable local checkout.

The retired `windows\\finish_install.cmd` intentionally exits rather than
install the earlier speculative CUDA 12 stack.
