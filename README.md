# CALVADOS–TEA IDP Simulator

Local application for designing elastin-like polypeptide (ELP) / IDP sequences, visualizing their motif arrangements and preparing CALVADOS simulations.

**Status:** Development software. The Streamlit designer, FASTA download, CPU/CUDA platform selector and CALVADOS input preparation are connected. Local execution through `python run.py` is available after preparation; the in-app run-manager/batch interface is not yet connected or end-to-end validated.

## Quick start (Windows / Anaconda Prompt)

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
conda activate calvados-elp-local
```

This installs our project **and CALVADOS automatically**. The Python dependencies come from the **upstream CALVADOS 0.9.1** `pyproject.toml`, including `openmm[cuda12]>=8.2,<8.5`, `MDAnalysis>=2.9,<2.11`, `mdtraj>=1.11,<1.12`, NumPy, pandas, Biopython, Jinja2, tqdm, Matplotlib, PyYAML, Pydantic 2, statsmodels, Numba and SciPy. We also install Streamlit, Plotly and OpenPyXL.

**Compatibility caveat:** CALVADOS's latest source currently documents Linux/POSIX support and requests CUDA-enabled OpenMM libraries by default. Native Windows CUDA installation may not work on every machine. If the environment fails to solve or import OpenMM, use **WSL2/Ubuntu** with a compatible NVIDIA driver, and execute the Linux instructions below. CPU-only users may still encounter CUDA-extra dependency installation issues; these are upstream packaging constraints, not a requirement to own a GPU.

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
conda activate calvados-elp-local
python -m calvados_library_builder.diagnostics
python -m streamlit run app.py
```

GPU/CUDA requires an NVIDIA GPU, appropriately installed drivers, and the correct OpenMM CUDA runtime. A CPU simulation does not require NVIDIA hardware. CALVADOS's current run input schema **only accepts `CPU` or `CUDA`**, even if your OpenMM installation reports additional platform names such as OpenCL/Reference. If you use macOS, select CPU.

An alternative to `conda env create` if you already have a suitable Python 3.11 environment:

```bash
python -m pip install -e ".[app,analysis,dev]"
```

Python alone cannot install your operating system's NVIDIA display/GPU driver.

## Use the application

1. Select two motif types, motif counts and an architecture type.
2. Edit the displayed motif blocks using drag/drop, changing block sizes or splitting blocks.
3. Export the resulting amino-acid sequence as FASTA.
4. In **Local simulation setup**, choose `CPU` or `CUDA`, set temperature, number of saved frames, output frequency and random seed.
5. Click **Prepare simulation files** to generate CALVADOS's `config.yaml`, `components.yaml`, `run.py`, FASTA and a copied residue-parameter file.
6. In a separate terminal with the same conda environment activated, enter the prepared run directory and run:

```bash
python run.py
```

Long simulations may take substantial time; start with a small test run rather than 50,000 frames. The current application does not yet offer a full simulation monitoring dashboard.

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
    streamlit_app.py        # local UI entry point
    motifs.py               # default/custom motifs
    sequences.py            # architecture generators
    visualization.py        # motif visuals
    architecture_editor.py  # interactive editing
    config.py               # simulation settings
    prepare.py              # FASTA + CALVADOS input preparation
    diagnostics.py          # OpenMM platforms and package versions
    runner.py               # existing local subprocess runner
    batch.py                # existing sequential queue
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

The test suite currently checks core sequence generation only. **An end-to-end simulation and native Windows CUDA installation have not yet been verified.** The old runner and queue are retained for further integration into the local Streamlit application.
