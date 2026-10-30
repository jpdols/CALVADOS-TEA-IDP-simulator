#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# ============================================================
# Project paths
# ============================================================

PACKAGE_DIR = Path(__file__).resolve().parent

# src/calvados_library_builder/config.py
# -> project root is two levels above PACKAGE_DIR
PROJECT_ROOT = PACKAGE_DIR.parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RUNS_DIR = PROJECT_ROOT / "runs"
EXAMPLES_DIR = PROJECT_ROOT / "examples"


# ============================================================
# CALVADOS defaults
# ============================================================

DEFAULT_TEMPERATURE = 370.0
DEFAULT_PH = 7.0
DEFAULT_IONIC_STRENGTH = 0.17

DEFAULT_BOX_SIZE = 50.0

DEFAULT_N_FRAMES = 50_000
DEFAULT_SAVE_EVERY = 1_000

DEFAULT_PLATFORM = "CUDA"

DEFAULT_TOPOLOGY = "center"

DEFAULT_RESTART = "checkpoint"
DEFAULT_RESTART_FILE = "restart.chk"

DEFAULT_VERBOSE = True

DEFAULT_MOLECULE_TYPE = "protein"
DEFAULT_NUMBER_OF_MOLECULES = 1
DEFAULT_RESTRAINT = False
DEFAULT_CHARGE_TERMINI = "both"

DEFAULT_REPLICATE = 1
DEFAULT_SEED = 1

DEFAULT_OUTPUT_DIR = RUNS_DIR


# ============================================================
# File settings
# ============================================================

DEFAULT_FASTA_NAME = "idp.fasta"

RESIDUE_FILE_TEMPLATE = (
    "residues_gamma_6p0_{temperature}K_argdefault_minus.csv"
)


# ============================================================
# Sequence settings
# ============================================================

DEFAULT_TARGET_AA = 420

VALID_AMINO_ACIDS = set(
    "ACDEFGHIKLMNPQRSTVWY"
)


# ============================================================
# Motif definitions
# ============================================================

MOTIFS = {
    "VPGVG": {
        "label": "VPGVG",
        "color": "#4C78A8",
    },
    "IPAVG": {
        "label": "IPAVG",
        "color": "#F2CF5B",
    },
    "VPGIG": {
        "label": "VPGIG",
        "color": "#54A24B",
    },
    "VPGKG": {
        "label": "VPGKG",
        "color": "#C13CFF",
    },
    "VPGEG": {
        "label": "VPGEG",
        "color": "#F28E2B",
    },
    "VPAVG": {
        "label": "VPAVG",
        "color": "#FF66B3",
    },
}


# ============================================================
# Simulation configuration
# ============================================================

@dataclass
class SimulationConfig:
    """
    Configuration for one CALVADOS simulation.

    Later the graphical interface can create this object
    directly from user input.
    """

    # Required values
    name: str
    sequence: str

    # Simulation conditions
    temperature: float = DEFAULT_TEMPERATURE
    pH: float = DEFAULT_PH
    ionic_strength: float = DEFAULT_IONIC_STRENGTH

    # Simulation box
    box_size: float = DEFAULT_BOX_SIZE

    # Simulation length
    n_frames: int = DEFAULT_N_FRAMES
    save_every: int = DEFAULT_SAVE_EVERY

    # Hardware
    platform: str = DEFAULT_PLATFORM

    # CALVADOS settings
    topology: str = DEFAULT_TOPOLOGY

    restart: str = DEFAULT_RESTART
    restart_file: str = DEFAULT_RESTART_FILE

    verbose: bool = DEFAULT_VERBOSE

    # Component settings
    molecule_type: str = DEFAULT_MOLECULE_TYPE
    number_of_molecules: int = DEFAULT_NUMBER_OF_MOLECULES
    restraint: bool = DEFAULT_RESTRAINT
    charge_termini: str = DEFAULT_CHARGE_TERMINI

    # Replicate / random seed
    replicate: int = DEFAULT_REPLICATE
    seed: int = DEFAULT_SEED

    # File / folder settings
    output_dir: Path = DEFAULT_OUTPUT_DIR
    residue_file: Path | None = None
    fasta_name: str = DEFAULT_FASTA_NAME

    # --------------------------------------------------------
    # Derived values
    # --------------------------------------------------------

    @property
    def steps(self) -> int:
        """
        Total CALVADOS integration steps.

        The existing workflow uses:

            steps = n_frames * save_every
        """

        return self.n_frames * self.save_every

    # --------------------------------------------------------
    # Paths
    # --------------------------------------------------------

    def resolve_residue_file(self) -> Path:
        """
        Return the residue parameter CSV.

        If the user provided a custom file, use that.

        Otherwise automatically select:

            data/residues_gamma_6p0_<TEMP>K_argdefault_minus.csv
        """

        if self.residue_file is not None:
            return Path(self.residue_file).expanduser().resolve()

        temperature_int = int(round(self.temperature))

        filename = RESIDUE_FILE_TEMPLATE.format(
            temperature=temperature_int
        )

        return (DATA_DIR / filename).resolve()

    def get_run_dir(self) -> Path:
        """
        Main directory for this simulation.

        Example:

            runs/
                E_AI_triblock/
        """

        return (
            Path(self.output_dir)
            / self.name
        ).expanduser().resolve()

    def get_input_dir(self) -> Path:
        """
        Input directory inside the simulation folder.

        Example:

            runs/E_AI_triblock/input/
        """

        return self.get_run_dir() / "input"

    def get_fasta_path(self) -> Path:
        """
        Full path to the automatically generated FASTA file.
        """

        return self.get_input_dir() / self.fasta_name


# ============================================================
# Validation
# ============================================================

def validate_config(
    config: SimulationConfig,
) -> None:
    """
    Validate the simulation configuration before preparation.
    """

    # --------------------------------------------------------
    # Name
    # --------------------------------------------------------

    if not config.name.strip():
        raise ValueError(
            "Simulation name cannot be empty."
        )

    # --------------------------------------------------------
    # Sequence
    # --------------------------------------------------------

    if not config.sequence.strip():
        raise ValueError(
            "Sequence cannot be empty."
        )

    sequence = config.sequence.strip().upper()

    invalid_residues = sorted(
        set(sequence) - VALID_AMINO_ACIDS
    )

    if invalid_residues:
        raise ValueError(
            "Sequence contains invalid residues: "
            + ", ".join(invalid_residues)
        )

    # --------------------------------------------------------
    # Conditions
    # --------------------------------------------------------

    if config.temperature <= 0:
        raise ValueError(
            "Temperature must be greater than 0 K."
        )

    if config.pH < 0 or config.pH > 14:
        raise ValueError(
            "pH must be between 0 and 14."
        )

    if config.ionic_strength < 0:
        raise ValueError(
            "Ionic strength cannot be negative."
        )

    # --------------------------------------------------------
    # Box
    # --------------------------------------------------------

    if config.box_size <= 0:
        raise ValueError(
            "Box size must be greater than zero."
        )

    # --------------------------------------------------------
    # Simulation length
    # --------------------------------------------------------

    if config.n_frames <= 0:
        raise ValueError(
            "Number of frames must be greater than zero."
        )

    if config.save_every <= 0:
        raise ValueError(
            "Save frequency must be greater than zero."
        )

    # --------------------------------------------------------
    # Components
    # --------------------------------------------------------

    if config.number_of_molecules <= 0:
        raise ValueError(
            "Number of molecules must be at least 1."
        )

    # --------------------------------------------------------
    # Replicate
    # --------------------------------------------------------

    if config.replicate < 1:
        raise ValueError(
            "Replicate number must be at least 1."
        )

    # --------------------------------------------------------
    # Residue file
    # --------------------------------------------------------

    residue_file = config.resolve_residue_file()

    if not residue_file.exists():
        raise FileNotFoundError(
            f"Residue parameter file not found: {residue_file}"
        )
