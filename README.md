> **New simplified app:** Run `python -m streamlit run app.py` and follow **Design → Simulate → Analyze**. See [STUDIO_GUIDE.md](STUDIO_GUIDE.md) for the new workflow, analysis definitions and execution debugging. The old detailed interface remains available with `python -m streamlit run legacy_app.py`.

# CALVADOS–TEA IDP Simulator

Local application for designing elastin-like polypeptide (ELP) / IDP sequences, visualizing their motif arrangements and preparing CALVADOS simulations.

**Status:** Local test candidate. The original full Streamlit app is restored: motif library, custom motifs, drag-and-drop architecture editor, sequence inspection, FASTA download, simulation settings, sequential batch queue, subprocess launch and live progress. CPU/CUDA selection and exit-code reporting have been updated. **Full end-to-end simulation on a real CALVADOS/OpenMM installation is still unverified.**

## Quick start (Windows / Anaconda Prompt)

**Use `streamlit run app.py` from the repository root.** This `app.py` is the recovered complete local interface, rather than the earlier minimal application.

Install [Git](https://git-scm.com/downloads) and [Miniforge](https://github.com/conda-forge/miniforge) or another working Conda distribution first.

1. Clone the source:

```bat
cd /d "E:\\Master thesis"
git clone https://github.com/jpdols/CALVADOS-TEA-IDP-simulator.git
cd CALVADOS-TEA-IDP-simulator
```

2. Create and activate the project's Python 3.11 environment:

```bat
conda env create -f environment.yml
conda activate calvados-tea-idp-simulator
```

This installs our project **and CALVADOS automatically**. Crucially, `environment.yml` now installs **OpenMM from conda-forge with `cuda-version=12` before pip installs the app**, so the CUDA backend is included in a fresh Windows Conda environment. The dependencies also include the pinned CALVADOS 0.9.1 code, `MDAnalysis`, `mdtraj`, Streamlit, Plotly and OpenPyXL. A compatible NVIDIA driver must already be installed on the host.

**CUDA tested locally (October 2026):** Windows, NVIDIA Quadro P1000 (4 GB), driver 573.71, CUDA 12.x; previously, a Python-only OpenMM setup produced `There is no registered Platform called "CUDA"`. Adding conda-forge OpenMM with `cuda-version=12` resolved the missing backend.

**Existing environments after `git pull`:** Git only updates source code; it does **not** install new packages. To upgrade an existing environment to match the repo file, activate the environment and run `conda env update -f environment.yml --prune` if its name is `calvados-tea-idp-simulator`, or install the CUDA backend directly using `conda install -c conda-forge "openmm>=8.2,<8.5" "cuda-version=12"`. Run `python -m openmm.testInstallation` afterward. Avoid mixing multiple incompatible OpenMM installations.

**Compatibility caveat:** CUDA requires supported NVIDIA hardware, driver and OpenMM plugins; installing these dependencies cannot supply a missing GPU or driver. For computers without a compatible GPU, the application can still run on the CPU. On hosts where the CUDA-enabled Conda environment fails to resolve, install with Python/CPU using the alternative setup below or use WSL2/Ubuntu.

3. Check which compute platforms your installation exposes:

```bat
python -m calvados_library_builder.diagnostics
```

4. Launch the interface:

```bat
python -m streamlit run app.py
```

Streamlit prints a local URL (normally `http://localhost:8501`) that you can open in your browser.

## Linux / WSL2 / macOS local setup

```bash
git clone https://github.com/jpdols/CALVADOS-TEA-IDP-simulator.git
cd CALVADOS-TEA-IDP-simulator
conda env create -f environment.yml
conda activate calvados-tea-idp-simulator
python -m calvados_library_builder.diagnostics
python -m streamlit run app.py
```

The default `environment.yml` requests CUDA 12 OpenMM from conda-forge; on a machine without a supported CUDA driver, use CPU for simulations. GPU/CUDA requires an NVIDIA GPU, appropriately installed drivers, and the correct OpenMM CUDA runtime. A CPU simulation does not require NVIDIA hardware. CALVADOS's current run input schema **only accepts `CPU` or `CUDA`**, even if your OpenMM installation reports additional platform names such as OpenCL/Reference. If you use macOS, select CPU.

An alternative to `conda env create` if you already have a suitable Python 3.11 environment:

```bash
python -m pip install -e ".[app,analysis,dev]"
```

Python alone cannot install your operating system's NVIDIA display/GPU driver.

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

The `pyproject.toml` carries the CALVADOS dependencies explicitly and installs CALVADOS itself from upstream commit `df7d12a3428a0151a9c4683e1300e086d67d8fa5`, corresponding to version 0.9.1 at inspection. This avoids silently updating CALVADOS when upstream `main` changes. Scientific simulations should record package versions (`python -m pip freeze`), force field, parameter-file checksum, temperature, ionic strength, pH, seed, simulation steps and output frequency.

See the [upstream CALVADOS installation instructions](https://github.com/KULL-Centre/CALVADOS#installation-instructions) and [dependency specification](https://github.com/KULL-Centre/CALVADOS/blob/main/pyproject.toml). Upstream instructions describe setting up OpenMM via conda-forge (including a CUDA 11.8 toolkit example), while its current Python package lists the CUDA 12 OpenMM extra. The approach in **this repo** follows its current package metadata; mixing both recipes without compatibility checks is not recommended.

## Testing

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

The test suite currently checks core sequence generation only. **An end-to-end simulation and native Windows CUDA installation have not yet been verified.** The runner and queue are now integrated with the restored Streamlit app; end-to-end testing on a local installation is the next step.

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
