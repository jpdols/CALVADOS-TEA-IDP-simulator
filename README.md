# CALVADOS–TEA IDP Simulator

An experimental Python package for motif-based elastin-like polypeptide (ELP) and intrinsically disordered protein (IDP) sequence design, visualization, and CALVADOS simulation preparation.

## Install

This repository uses the **src/** Python package layout. With Python 3.10 and Git installed:

```bash
git clone https://github.com/jpdols/CALVADOS-TEA-IDP-simulator.git
cd CALVADOS-TEA-IDP-simulator
python -m pip install -e ".[app,analysis,dev]"
```

Installing the project automatically requests CALVADOS from the [upstream CALVADOS repository](https://github.com/KULL-Centre/CALVADOS). **Important:** It currently tracks upstream `main`; pin a tested commit and freeze the complete environment before publishing reproducible simulation results. GPU execution also requires compatible OpenMM/CUDA libraries and GPU drivers.

Alternatively, use `conda env create -f environment.yml` if its packages resolve in your environment. On DelftBlue, prepare a separate tested CUDA environment before submitting SLURM jobs.

## Start the visual designer

```bash
streamlit run app.py
```

The app provides a two-motif builder, an interactive motif-block editor, two sequence views, and FASTA export. It **does not yet** provide a complete simulation launch/control interface.

## Package contents

| Module | Function |
|---|---|
| `motifs.py` | Default and custom motif definitions |
| `sequences.py` | Two-motif architecture generators |
| `architecture_editor.py` | Interactive Streamlit motif-block editing |
| `visualization.py` | Compact and detailed architecture visualizations |
| `config.py` | Simulation parameter defaults and validation |
| `prepare.py` | FASTA, CALVADOS config and component generation |
| `runner.py` | Local subprocess launch and DCD progress inspection |
| `batch.py` | Sequential local simulation queue |
| `streamlit_app.py` | Initial visual designer entry point |

## Development roadmap

1. Test end-to-end CALVADOS installation and `prepare.py` against a pinned upstream CALVADOS commit.
2. Make replicate seeds, run directories and metadata reproducible; test local runner status and failures.
3. Add SLURM generation and status tracking for DelftBlue.
4. Integrate the validated master Rg/kinetics analysis from the thesis project.
5. Add expanded tests for Streamlit editor state, import/export, CALVADOS configuration, and long-running jobs.

## Scientific reproducibility

Keep source and parameter checksums, force-field version, temperature, pH, ionic strength, sequence, simulation seed, steps, output frequency, and trajectory file identities together in a machine-readable run manifest. Residue parameter files required by the current `config.py` are expected under `data/` but **have not been committed to this repository**. Supply them before preparing simulations. Never commit `.dcd` trajectories, checkpoints or other bulky simulation output.

## Tests

```bash
python -m pytest -q
```

The repository is a development snapshot, not a scientifically validated released simulator.
