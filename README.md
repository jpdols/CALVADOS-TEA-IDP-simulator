# CALVADOS–TEA IDP Simulator

## Windows desktop shortcut (portable)

After the Conda/Python environment has been installed, double-click
[`windows/install_elp_studio.cmd`](windows/install_elp_studio.cmd)
once to create an **ELP Studio** shortcut on your Desktop. The installer
finds the repository automatically, searches for an environment with
Streamlit and ELP Studio installed, and stores machine-specific paths
only locally. No fixed `C:\\`/`E:\\` drive or Conda environment
name is required.

The desktop icon starts the app and opens your browser. For setup,
custom icons, logs and stopping the local server, see
[WINDOWS_LAUNCHER.md](WINDOWS_LAUNCHER.md).


Local application for designing elastin-like polypeptide (ELP) / IDP sequences, visualizing their motif arrangements and preparing CALVADOS simulations.

**Status:** Local test candidate. The original full Streamlit app is restored: motif library, custom motifs, drag-and-drop architecture editor, sequence inspection, FASTA download, simulation settings, sequential batch queue, subprocess launch and live progress. CPU/CUDA selection and exit-code reporting have been updated. **Full end-to-end simulation on a real CALVADOS/OpenMM installation is still unverified.**

## Install (Windows, Linux, or macOS)

**One setup for everyone:** the public installer creates a Conda environment named
`calvados-tea-idp-simulator`. It first attempts OpenMM **CUDA** when an NVIDIA
GPU/driver is detected; it runs a real CUDA force calculation. If GPU setup
cannot resolve or CUDA fails, it falls back to **CPU**. Computers without an
NVIDIA GPU install the CPU backend directly. Both use the same application.

Prerequisites: [Miniforge](https://github.com/conda-forge/miniforge) (or
another Conda installation) and [Git](https://git-scm.com/downloads).
Use a Conda-enabled terminal (Anaconda Prompt on Windows).

```bash
git clone https://github.com/jpdols/CALVADOS-TEA-IDP-simulator.git
cd CALVADOS-TEA-IDP-simulator
python install.py
conda activate calvados-tea-idp-simulator
python -m streamlit run app.py
```

If already cloned, run `git pull origin main` from the repository before
`python install.py`. On Windows, the equivalent installer shortcut is
`windows\\install_from_working_env.cmd`, which now simply calls this same
portable installer: it does **not** clone any existing user's environment.

The install uses Python 3.10, OpenMM 8.2, CALVADOS 0.8.0 pinned to a
**public GitHub revision**, and Conda-managed scientific dependencies.
It does **not** require any local CALVADOS checkout or fixed disk path.
CUDA attempts use `cudatoolkit=11.8.0`; CPU fallback omits the toolkit.

For diagnostics, updating, and existing-environment protections:

```bash
python install.py --check
python install.py --update
python install.py --dry-run
```

To force a CPU-only installation, use `python install.py --cpu`; to
attempt CUDA even if automatic NVIDIA detection fails, use
`python install.py --gpu`. The installer will **not overwrite an existing
environment**; `--update` updates the ELP Studio code in an existing
compatible environment without changing the simulation engine. The app
continues to expose both CPU and CUDA options; use the backend that passed
the installer's force-calculation check.

The Windows Desktop shortcut can be created after installation by running
`windows\\install_elp_studio.cmd` from the activated environment.

**Validation scope:** GitHub unit tests verify package-independent
application logic on Linux. They do **not** validate CUDA hardware. CUDA
is tested locally by the installer itself. A short real CALVADOS run should
be performed before production simulations.

See [INSTALL_GPU_WINDOWS.md](INSTALL_GPU_WINDOWS.md) for details about the
GPU-first/CPU-fallback strategy and common errors.

## Use the application

1. Select two motif types, motif counts and an architecture type.
2. Edit the displayed motif blocks using drag/drop, changing block sizes or splitting blocks.
3. Export the resulting amino-acid sequence as FASTA.
4. In **Simulation settings**, choose `CPU` or `CUDA`, set temperature, saved frames and output frequency.
5. Enter a batch name and select **Add design to run** to queue sequences, or **Add design and run** to begin the queue. The app prepares `config.yaml`, `components.yaml`, `run.py`, FASTA and the temperature-dependent residue table.
6. The app can start simulations and display live progress. Alternatively, execute a prepared simulation manually from a terminal:

```bash
python run.py
```

Start with a very small CPU test (e.g. 10–100 saved frames) instead of the default 50,000 frames. The monitoring UI reports progress using DCD frames and treats nonzero process exits as failures. A full CPU/CUDA smoke test is still required.

### Required temperature-dependent residue parameter files

The existing thesis-era preparation code expects files following the pattern

```text
data/residues_gamma_6p0_370K_argdefault_minus.csv
data/residues_gamma_6p0_300K_argdefault_minus.csv
```

for the selected temperature. **All 11 thesis-specific tables (300 K to 400 K in 10 K increments) are now included in `data/`.** The application selects the matching temperature file automatically for these temperatures. For other temperatures, supply a validated CSV using the CLI `--residue-file` option. These tables are supplied as research inputs, not generated automatically by CALVADOS.

### CLI preparation

With the environment activated:

```bash
python -m calvados_library_builder.prepare --name test_vpgvg --sequence VPGVGVPGVGVPGVG --temperature 370 --platform CPU --frames 100 --save-every 1000 --seed 1 --residue-file /absolute/path/to/your/residues_370K.csv
```

For Windows paths, put the path in double quotes. To run the generated `run.py`, change to its output folder.

## Where the code lives

```text
app.py
src/calvados_library_builder/
    streamlit_app.py        # simplified alternative UI entry point
    motifs.py               # default/custom motifs
    sequences.py            # architecture generators
    visualization.py        # motif visuals
    architecture_editor.py  # interactive editing
    config.py               # simulation settings
    prepare.py              # FASTA + CALVADOS input preparation
    diagnostics.py          # OpenMM platforms and package versions
    runner.py               # local subprocess runner and run state
    run_worker.py           # writes process exit code after completion
    batch.py                # sequential queue and progress tracker
tests/
data/                       # user's custom temperature parameter CSVs
runs/                       # simulation output, excluded from Git
```

## Dependency and versioning policy

The installer obtains CALVADOS 0.8.0 from a pinned public upstream
revision and preserves the conda-forge OpenMM 8.2 GPU/CPU binary.
Scientific reproducibility additionally requires recording the force-field
residue table, simulation seed, temperature, ionic strength, pH, steps,
and installed package versions. See `install.py` for the pinned source
revision and platform validation.

## Testing

```bash
python -m pip install --no-deps -e ".[dev]"
python -m pytest -q
```

CI checks the Python application/unit tests without GPU access. The local installer independently checks OpenMM forces on CPU and (when available) CUDA. A full CALVADOS smoke simulation on the target computer is still required.

## Updating the code from your laptop

Once you have cloned the repo, open an Anaconda Prompt in the repository and run:

```bash
git pull origin main
```

After editing a Python file, use:

```bash
git status
git add app.py src/calvados_library_builder/
git commit -m "Describe my local improvement"
git push origin main
```

On another machine, `git pull origin main` retrieves the change. If you want to change just one script, commit only that script instead of all files. Avoid committing the `runs/` outputs or large trajectory data. When sharing an error here, include `python -m calvados_library_builder.diagnostics` output plus the relevant error log. Please do not publish private local filesystem paths or credentials in logs.
