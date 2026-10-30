#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict


# ============================================================
# Default motifs
# ============================================================

DEFAULT_MOTIFS = {
    "VPGVG": {
        "label": "VPGVG",
        "sequence": "VPGVG",
        "color": "#4C78A8",
    },
    "IPAVG": {
        "label": "IPAVG",
        "sequence": "IPAVG",
        "color": "#F2CF5B",
    },
    "VPGIG": {
        "label": "VPGIG",
        "sequence": "VPGIG",
        "color": "#54A24B",
    },
    "VPGKG": {
        "label": "VPGKG",
        "sequence": "VPGKG",
        "color": "#FF66B3",
    },
    "VPGEG": {
        "label": "VPGEG",
        "sequence": "VPGEG",
        "color": "#F28E2B",
    },
    "VPAVG": {
        "label": "VPAVG",
        "sequence": "VPAVG",
        "color": "#20B8B0",
    },
    "RGD": {
        "label": "RGD block",
        "sequence": "AVTGRGDSPASS",
        "color": "#7944AC",
    },
}


# ============================================================
# Amino-acid validation
# ============================================================

VALID_AMINO_ACIDS = set(
    "ACDEFGHIKLMNPQRSTVWY"
)


# ============================================================
# Motif data structure
# ============================================================

@dataclass(frozen=True)
class Motif:
    """
    Representation of one sequence motif.

    Parameters
    ----------
    name
        Unique motif identifier.

    sequence
        One-letter amino-acid sequence.

    color
        HEX color used in the graphical interface.

    label
        Optional display label.
    """

    name: str
    sequence: str
    color: str
    label: str | None = None

    @property
    def display_label(self) -> str:
        """
        Label shown in the graphical interface.
        """

        if self.label:
            return self.label

        return self.name

    @property
    def length(self) -> int:
        """
        Number of amino acids in the motif.
        """

        return len(self.sequence)


# ============================================================
# Validation helpers
# ============================================================

def normalize_motif_name(
    name: str,
) -> str:
    """
    Normalize a motif name.

    Examples
    --------
    " vpgfg " -> "VPGFG"
    """

    return name.strip().upper()


def normalize_sequence(
    sequence: str,
) -> str:
    """
    Normalize a motif sequence.

    Removes whitespace and converts to uppercase.
    """

    return (
        sequence
        .replace(" ", "")
        .replace("\n", "")
        .replace("\r", "")
        .replace("\t", "")
        .upper()
    )


def validate_motif_sequence(
    sequence: str,
) -> None:
    """
    Validate that a motif contains only standard
    one-letter amino-acid codes.
    """

    sequence = normalize_sequence(
        sequence
    )

    if not sequence:
        raise ValueError(
            "Motif sequence cannot be empty."
        )

    invalid = sorted(
        set(sequence)
        - VALID_AMINO_ACIDS
    )

    if invalid:
        raise ValueError(
            "Motif contains invalid amino-acid codes: "
            + ", ".join(invalid)
        )


def validate_hex_color(
    color: str,
) -> None:
    """
    Validate a HEX color.

    Accepted example:
        #4C78A8
    """

    if not isinstance(
        color,
        str,
    ):
        raise ValueError(
            "Color must be a string."
        )

    color = color.strip()

    if not re.fullmatch(
        r"#[0-9A-Fa-f]{6}",
        color,
    ):
        raise ValueError(
            "Color must be a 6-digit HEX value, "
            "for example #4C78A8."
        )


# ============================================================
# Default motif collection
# ============================================================

def get_default_motifs() -> Dict[str, Motif]:
    """
    Return the built-in motif collection.

    A new dictionary is returned each time so callers
    can modify it without changing the defaults.
    """

    motifs: Dict[str, Motif] = {}

    for name, data in DEFAULT_MOTIFS.items():

        motifs[name] = Motif(
            name=name,
            sequence=data["sequence"],
            color=data["color"],
            label=data["label"],
        )

    return motifs


# ============================================================
# Custom motif creation
# ============================================================

def create_motif(
    name: str,
    sequence: str,
    color: str,
    label: str | None = None,
) -> Motif:
    """
    Create and validate a new motif.

    Parameters
    ----------
    name
        Unique motif identifier.

    sequence
        Amino-acid sequence.

    color
        HEX color.

    label
        Optional display name.

    Returns
    -------
    Motif
        Validated motif object.
    """

    normalized_name = normalize_motif_name(
        name
    )

    normalized_sequence = normalize_sequence(
        sequence
    )

    if not normalized_name:
        raise ValueError(
            "Motif name cannot be empty."
        )

    validate_motif_sequence(
        normalized_sequence
    )

    validate_hex_color(
        color
    )

    if label is not None:
        label = label.strip()

        if not label:
            label = None

    return Motif(
        name=normalized_name,
        sequence=normalized_sequence,
        color=color.upper(),
        label=label,
    )


# ============================================================
# Add motif to collection
# ============================================================

def add_motif(
    motifs: Dict[str, Motif],
    motif: Motif,
    overwrite: bool = False,
) -> Dict[str, Motif]:
    """
    Add a motif to a motif dictionary.

    Parameters
    ----------
    motifs
        Existing motif dictionary.

    motif
        Motif to add.

    overwrite
        Whether an existing motif with the same name
        may be replaced.

    Returns
    -------
    dict
        Updated copy of the motif dictionary.
    """

    updated = dict(
        motifs
    )

    if (
        motif.name in updated
        and not overwrite
    ):
        raise ValueError(
            f"Motif '{motif.name}' already exists."
        )

    updated[motif.name] = motif

    return updated


# ============================================================
# Remove motif
# ============================================================

def remove_motif(
    motifs: Dict[str, Motif],
    motif_name: str,
) -> Dict[str, Motif]:
    """
    Remove a motif from a motif collection.

    Returns a copy and does not modify the original dictionary.
    """

    motif_name = normalize_motif_name(
        motif_name
    )

    updated = dict(
        motifs
    )

    if motif_name not in updated:
        raise KeyError(
            f"Motif '{motif_name}' does not exist."
        )

    del updated[
        motif_name
    ]

    return updated


# ============================================================
# Utility functions
# ============================================================

def motif_names(
    motifs: Dict[str, Motif],
) -> list[str]:
    """
    Return motif names in dictionary order.
    """

    return list(
        motifs.keys()
    )


def motif_sequences(
    motifs: Dict[str, Motif],
) -> dict[str, str]:
    """
    Return mapping:

        motif name -> amino-acid sequence
    """

    return {
        name: motif.sequence
        for name, motif
        in motifs.items()
    }


def motif_colors(
    motifs: Dict[str, Motif],
) -> dict[str, str]:
    """
    Return mapping:

        motif name -> HEX color
    """

    return {
        name: motif.color
        for name, motif
        in motifs.items()
    }


# ============================================================
# Simple standalone test
# ============================================================

if __name__ == "__main__":

    motifs = get_default_motifs()

    print("Default motifs:")

    for motif in motifs.values():
        print(
            f"{motif.name}: "
            f"{motif.sequence} "
            f"({motif.length} aa) "
            f"{motif.color}"
        )

    test_motif = create_motif(
        name="VPGFG",
        sequence="VPGFG",
        color="#00AEEF",
    )

    motifs = add_motif(
        motifs,
        test_motif,
    )

    print()
    print("Added custom motif:")
    print(
        motifs["VPGFG"]
    )
