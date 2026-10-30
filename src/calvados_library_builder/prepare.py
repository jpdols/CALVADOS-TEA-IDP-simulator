#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import shutil

from pathlib import Path

from .config import (
    DEFAULT_BOX_SIZE,
    DEFAULT_CHARGE_TERMINI,
    DEFAULT_FASTA_NAME,
    DEFAULT_IONIC_STRENGTH,
    DEFAULT_MOLECULE_TYPE,
    DEFAULT_N_FRAMES,
    DEFAULT_NUMBER_OF_MOLECULES,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PH,
    DEFAULT_PLATFORM,
    DEFAULT_RESTART,
    DEFAULT_RESTART_FILE,
    DEFAULT_SAVE_EVERY,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOPOLOGY,
    SimulationConfig,
    validate_config,
)


# ============================================================
# FASTA writing
# ============================================================

def write_fasta(
    name: str,
    sequence: str,
    fasta_path: Path,
) -> Path:
    """
    Write a single-protein FASTA file.
    """

    fasta_path = Path(
        fasta_path
    )

    fasta_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    sequence = (
        sequence
        .strip()
        .upper()
    )

    fasta_text = (
        f">{name}\n"
        f"{sequence}\n"
    )

    fasta_path.write_text(
        fasta_text,
        encoding="utf-8",
    )

    return fasta_path


# ============================================================
# Resolve simulation directory
# ============================================================

def resolve_run_dir(
    config: SimulationConfig,
    batch_dir: Path | None = None,
) -> Path:
    """
    Determine where a prepared simulation should be stored.

    Without batch_dir:
        runs/<simulation_name>/

    With batch_dir:
        <batch_dir>/<simulation_name>/
    """

    if batch_dir is None:

        return (
            Path(config.output_dir)
            / config.name
        ).expanduser().resolve()

    return (
        Path(batch_dir)
        .expanduser()
        .resolve()
        / config.name
    )


# ============================================================
# Prepare CALVADOS simulation
# ============================================================

def prepare_simulation(
    config: SimulationConfig,
    batch_dir: Path | None = None,
) -> Path:
    """
    Prepare one CALVADOS simulation.

    Parameters
    ----------
    config
        Simulation configuration.

    batch_dir
        Optional parent directory for a simulation batch.

        Example:
            runs/VGIP_screen/

        The resulting simulation directory becomes:
            runs/VGIP_screen/VGIP_even/

    Returns
    -------
    Path
        Prepared simulation directory.
    """

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    config.name = (
        config.name
        .strip()
    )

    config.sequence = (
        config.sequence
        .strip()
        .upper()
    )

    validate_config(
        config
    )


    # --------------------------------------------------------
    # Resolve directories
    # --------------------------------------------------------

    run_dir = resolve_run_dir(
        config=config,
        batch_dir=batch_dir,
    )

    input_dir = (
        run_dir
        / "input"
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    input_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    # --------------------------------------------------------
    # FASTA
    # --------------------------------------------------------

    fasta_path = (
        input_dir
        / config.fasta_name
    )

    write_fasta(
        name=config.name,
        sequence=config.sequence,
        fasta_path=fasta_path,
    )


    # --------------------------------------------------------
    # Residue parameter file
    # --------------------------------------------------------

    source_residue_file = (
        config.resolve_residue_file()
    )

    if not source_residue_file.exists():

        raise FileNotFoundError(
            "Residue parameter file not found: "
            f"{source_residue_file}"
        )

    local_residue_file = (
        input_dir
        / source_residue_file.name
    )

    if (
        source_residue_file.resolve()
        != local_residue_file.resolve()
    ):

        shutil.copy2(
            source_residue_file,
            local_residue_file,
        )


    # --------------------------------------------------------
    # Paths written into components.yaml
    #
    # These are deliberately relative to the simulation folder.
    # --------------------------------------------------------

    fasta_for_calvados = (
        Path("input")
        / config.fasta_name
    )

    residues_for_calvados = (
        Path("input")
        / local_residue_file.name
    )


    # --------------------------------------------------------
    # Lazy CALVADOS import
    #
    # This keeps normal Streamlit reruns fast.
    # --------------------------------------------------------

    from calvados.cfg import (
        Config,
        Components,
    )


    # --------------------------------------------------------
    # config.yaml / CALVADOS run configuration
    # --------------------------------------------------------

    calvados_config = Config(
        sysname=config.name,

        box=[
            config.box_size,
            config.box_size,
            config.box_size,
        ],

        temp=config.temperature,

        ionic=config.ionic_strength,

        pH=config.pH,

        topol=config.topology,

        wfreq=config.save_every,

        steps=config.steps,

        runtime=0,

        platform=config.platform,
        random_number_seed=config.seed,

        restart=config.restart,

        frestart=config.restart_file,

        verbose=config.verbose,
    )

    calvados_config.write(
        run_dir,
        name="config.yaml",
    )


    # --------------------------------------------------------
    # components.yaml
    # --------------------------------------------------------

    components = Components(
        molecule_type=config.molecule_type,

        nmol=config.number_of_molecules,

        restraint=config.restraint,

        charge_termini=config.charge_termini,

        fresidues=str(
            residues_for_calvados
        ),

        ffasta=str(
            fasta_for_calvados
        ),
    )

    components.add(
        name=config.name
    )

    components.write(
        run_dir,
        name="components.yaml",
    )


    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )

    print(
        "CALVADOS simulation prepared"
    )

    print(
        "=" * 70
    )

    print(
        f"Name:              "
        f"{config.name}"
    )

    print(
        f"Sequence length:   "
        f"{len(config.sequence)} aa"
    )

    print(
        f"Temperature:       "
        f"{config.temperature} K"
    )

    print(
        f"Ionic strength:    "
        f"{config.ionic_strength} M"
    )

    print(
        f"pH:                "
        f"{config.pH}"
    )

    print(
        f"Box:               "
        f"{config.box_size} × "
        f"{config.box_size} × "
        f"{config.box_size}"
    )

    print(
        f"Frames:            "
        f"{config.n_frames}"
    )

    print(
        f"Save every:        "
        f"{config.save_every}"
    )

    print(
        f"Total steps:       "
        f"{config.steps:,}"
    )

    print(
        f"Platform:          "
        f"{config.platform}"
    )

    print(
        f"Molecule type:     "
        f"{config.molecule_type}"
    )

    print(
        f"Number molecules:  "
        f"{config.number_of_molecules}"
    )

    print(
        f"Charge termini:    "
        f"{config.charge_termini}"
    )

    print(
        f"Replicate:         "
        f"{config.replicate}"
    )

    if batch_dir is not None:

        print(
            f"Batch directory:   "
            f"{Path(batch_dir).resolve()}"
        )

    print()

    print(
        f"Run directory:     "
        f"{run_dir}"
    )

    print(
        f"FASTA:             "
        f"{fasta_path}"
    )

    print(
        f"Residue file:      "
        f"{local_residue_file}"
    )

    print()

    print(
        "Created:"
    )

    print(
        "  config.yaml"
    )

    print(
        "  components.yaml"
    )

    print(
        f"  input/{config.fasta_name}"
    )

    print(
        f"  input/{local_residue_file.name}"
    )

    run_script = (
        run_dir
        / "run.py"
    )

    if run_script.exists():

        print(
            "  run.py"
        )

    else:

        print(
            "  run.py: not found after preparation"
        )

    print(
        "=" * 70
    )

    print()

    return run_dir


# ============================================================
# CLI arguments
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Prepare a CALVADOS simulation."
        )
    )

    parser.add_argument(
        "--name",
        required=True,
        help=(
            "Simulation / sequence name."
        ),
    )

    parser.add_argument(
        "--sequence",
        required=True,
        help=(
            "One-letter amino-acid sequence."
        ),
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
    )

    parser.add_argument(
        "--ionic-strength",
        type=float,
        default=DEFAULT_IONIC_STRENGTH,
    )

    parser.add_argument(
        "--pH",
        type=float,
        default=DEFAULT_PH,
    )

    parser.add_argument(
        "--frames",
        type=int,
        default=DEFAULT_N_FRAMES,
    )

    parser.add_argument(
        "--save-every",
        type=int,
        default=DEFAULT_SAVE_EVERY,
    )

    parser.add_argument(
        "--box-size",
        type=float,
        default=DEFAULT_BOX_SIZE,
    )

    parser.add_argument(
        "--platform",
        default=DEFAULT_PLATFORM,
    )

    parser.add_argument(
        "--topology",
        default=DEFAULT_TOPOLOGY,
    )

    parser.add_argument(
        "--restart",
        default=DEFAULT_RESTART,
    )

    parser.add_argument(
        "--restart-file",
        default=DEFAULT_RESTART_FILE,
    )

    parser.add_argument(
        "--charge-termini",
        default=DEFAULT_CHARGE_TERMINI,
    )

    parser.add_argument(
        "--nmol",
        type=int,
        default=DEFAULT_NUMBER_OF_MOLECULES,
    )

    parser.add_argument(
        "--residue-file",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--fasta-name",
        default=DEFAULT_FASTA_NAME,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )

    parser.add_argument(
        "--batch-dir",
        type=Path,
        default=None,
        help=(
            "Optional batch directory. "
            "If supplied, the simulation is prepared as "
            "<batch-dir>/<simulation-name>/."
        ),
    )

    parser.add_argument("--seed", type=int, default=1)

    parser.add_argument(
        "--replicate",
        type=int,
        default=1,
    )

    return parser.parse_args()


# ============================================================
# Config from CLI
# ============================================================

def config_from_args(
    args,
) -> SimulationConfig:

    return SimulationConfig(
        name=args.name,

        sequence=args.sequence,

        temperature=args.temperature,

        pH=args.pH,

        ionic_strength=(
            args.ionic_strength
        ),

        box_size=args.box_size,

        n_frames=args.frames,

        save_every=args.save_every,

        platform=args.platform,

        topology=args.topology,

        restart=args.restart,

        restart_file=(
            args.restart_file
        ),

        molecule_type=(
            DEFAULT_MOLECULE_TYPE
        ),

        number_of_molecules=(
            args.nmol
        ),

        restraint=False,

        charge_termini=(
            args.charge_termini
        ),

        replicate=args.replicate,
        seed=args.seed,

        output_dir=args.output_dir,

        residue_file=(
            args.residue_file
        ),

        fasta_name=args.fasta_name,
    )


# ============================================================
# Main
# ============================================================

def main():

    args = parse_args()

    config = config_from_args(
        args
    )

    prepare_simulation(
        config=config,
        batch_dir=args.batch_dir,
    )


if __name__ == "__main__":

    main()
