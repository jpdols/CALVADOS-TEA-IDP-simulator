#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .motifs import Motif


# ============================================================
# Sequence design result
# ============================================================

@dataclass
class SequenceDesign:
    """
    Result of a motif-based sequence design.

    Attributes
    ----------
    motif_order
        Ordered list of motif names.

        Example:
            [
                "VPGVG",
                "VPGVG",
                "IPAVG",
                "IPAVG",
            ]

    sequence
        Full concatenated amino-acid sequence.

    motif_counts
        Number of occurrences of each motif.
    """

    motif_order: List[str]
    sequence: str
    motif_counts: Dict[str, int]

    @property
    def total_motifs(self) -> int:
        """
        Total number of motif instances.
        """

        return len(self.motif_order)

    @property
    def total_aa(self) -> int:
        """
        Total number of amino acids.
        """

        return len(self.sequence)


# ============================================================
# General helpers
# ============================================================

def motif_order_to_sequence(
    motif_order: list[str],
    motifs: dict[str, Motif],
) -> str:
    """
    Convert an ordered list of motif names into
    a full amino-acid sequence.

    Example
    -------
    motif_order:
        ["VPGVG", "IPAVG"]

    result:
        "VPGVGIPAVG"
    """

    sequence_parts = []

    for motif_name in motif_order:

        if motif_name not in motifs:
            raise KeyError(
                f"Unknown motif: '{motif_name}'"
            )

        sequence_parts.append(
            motifs[motif_name].sequence
        )

    return "".join(
        sequence_parts
    )


def count_motifs(
    motif_order: list[str],
) -> dict[str, int]:
    """
    Count how many times each motif occurs.
    """

    counts: dict[str, int] = {}

    for motif_name in motif_order:

        counts[motif_name] = (
            counts.get(
                motif_name,
                0,
            )
            + 1
        )

    return counts


def create_design(
    motif_order: list[str],
    motifs: dict[str, Motif],
) -> SequenceDesign:
    """
    Create a SequenceDesign from an ordered motif list.
    """

    sequence = motif_order_to_sequence(
        motif_order=motif_order,
        motifs=motifs,
    )

    motif_counts = count_motifs(
        motif_order
    )

    return SequenceDesign(
        motif_order=list(motif_order),
        sequence=sequence,
        motif_counts=motif_counts,
    )


# ============================================================
# Validation
# ============================================================

def validate_two_motif_inputs(
    motif_a: str,
    count_a: int,
    motif_b: str,
    count_b: int,
    motifs: dict[str, Motif],
) -> None:
    """
    Validate inputs for the two-motif builder.
    """

    if motif_a not in motifs:
        raise KeyError(
            f"Unknown motif A: '{motif_a}'"
        )

    if motif_b not in motifs:
        raise KeyError(
            f"Unknown motif B: '{motif_b}'"
        )

    if count_a < 0:
        raise ValueError(
            "Motif A count cannot be negative."
        )

    if count_b < 0:
        raise ValueError(
            "Motif B count cannot be negative."
        )

    if count_a == 0 and count_b == 0:
        raise ValueError(
            "At least one motif count must be greater than zero."
        )


# ============================================================
# Alternating architecture
# ============================================================

def build_alternating_order(
    motif_a: str,
    count_a: int,
    motif_b: str,
    count_b: int,
) -> list[str]:
    """
    Build an alternating motif order.

    Example
    -------
    A = 3
    B = 3

    A B A B A B

    If counts are unequal, the remaining motif is
    appended after the other motif is exhausted.

    Example
    -------
    A = 5
    B = 2

    A B A B A A A
    """

    order: list[str] = []

    a_left = count_a
    b_left = count_b

    while a_left > 0 or b_left > 0:

        if a_left > 0:
            order.append(
                motif_a
            )

            a_left -= 1

        if b_left > 0:
            order.append(
                motif_b
            )

            b_left -= 1

    return order


# ============================================================
# Diblock architecture
# ============================================================

def build_diblock_order(
    motif_a: str,
    count_a: int,
    motif_b: str,
    count_b: int,
) -> list[str]:
    """
    Build an A-B diblock.

    Example
    -------
    A = 4
    B = 3

    A A A A B B B
    """

    return (
        [motif_a] * count_a
        + [motif_b] * count_b
    )


# ============================================================
# Triblock architecture
# ============================================================

def build_triblock_order(
    motif_a: str,
    count_a: int,
    motif_b: str,
    count_b: int,
) -> list[str]:
    """
    Build an A-B-A triblock.

    Motif A is split as evenly as possible between
    the two outer blocks.

    Example
    -------
    A = 6
    B = 4

    A A A B B B B A A A

    Example with odd A count
    ------------------------
    A = 5
    B = 4

    A A B B B B A A A

    The extra A motif is placed in the final block.
    """

    left_a = (
        count_a
        // 2
    )

    right_a = (
        count_a
        - left_a
    )

    return (
        [motif_a] * left_a
        + [motif_b] * count_b
        + [motif_a] * right_a
    )


# ============================================================
# Symmetric inverse triblock
# ============================================================

def build_inverse_triblock_order(
    motif_a: str,
    count_a: int,
    motif_b: str,
    count_b: int,
) -> list[str]:
    """
    Build a B-A-B triblock.

    This complements the normal A-B-A triblock and
    can be useful when the identity of the central
    motif block matters.

    Example
    -------
    A = 4
    B = 6

    B B B A A A A B B B
    """

    left_b = (
        count_b
        // 2
    )

    right_b = (
        count_b
        - left_b
    )

    return (
        [motif_b] * left_b
        + [motif_a] * count_a
        + [motif_b] * right_b
    )


# ============================================================
# Repeating block architecture
# ============================================================

def build_block_pattern_order(
    motif_a: str,
    count_a: int,
    motif_b: str,
    count_b: int,
    block_size_a: int = 1,
    block_size_b: int = 1,
) -> list[str]:
    """
    Build repeated blocks of A and B.

    Example
    -------
    block_size_a = 3
    block_size_b = 2

    A A A B B A A A B B ...

    If the motif counts are not exact multiples of the
    block sizes, the final block is shortened.
    """

    if block_size_a < 1:
        raise ValueError(
            "Block size A must be at least 1."
        )

    if block_size_b < 1:
        raise ValueError(
            "Block size B must be at least 1."
        )

    order: list[str] = []

    a_left = count_a
    b_left = count_b

    while a_left > 0 or b_left > 0:

        if a_left > 0:

            a_take = min(
                block_size_a,
                a_left,
            )

            order.extend(
                [motif_a]
                * a_take
            )

            a_left -= a_take

        if b_left > 0:

            b_take = min(
                block_size_b,
                b_left,
            )

            order.extend(
                [motif_b]
                * b_take
            )

            b_left -= b_take

    return order


# ============================================================
# Evenly distributed architecture
# ============================================================

def build_evenly_distributed_order(
    motif_a: str,
    count_a: int,
    motif_b: str,
    count_b: int,
) -> list[str]:
    """
    Distribute two motif types as evenly as possible.

    Unlike the simple alternating architecture, this
    tries to spread the less abundant motif across
    the complete sequence instead of placing excess
    copies at one end.

    Example
    -------
    A = 8
    B = 3

    approximate result:

    A A B A A B A A B A A

    This is useful for unequal motif ratios.
    """

    total = (
        count_a
        + count_b
    )

    if total == 0:
        return []

    order: list[str] = []

    used_a = 0
    used_b = 0

    for position in range(total):

        target_a = (
            (position + 1)
            * count_a
            / total
        )

        target_b = (
            (position + 1)
            * count_b
            / total
        )

        deficit_a = (
            target_a
            - used_a
        )

        deficit_b = (
            target_b
            - used_b
        )

        if (
            deficit_a >= deficit_b
            and used_a < count_a
        ):
            order.append(
                motif_a
            )

            used_a += 1

        elif used_b < count_b:

            order.append(
                motif_b
            )

            used_b += 1

        else:

            order.append(
                motif_a
            )

            used_a += 1

    return order


# ============================================================
# Main two-motif builder
# ============================================================

def build_two_motif_design(
    motif_a: str,
    count_a: int,
    motif_b: str,
    count_b: int,
    architecture: str,
    motifs: dict[str, Motif],
    block_size_a: int = 1,
    block_size_b: int | None = None,
) -> SequenceDesign:
    """
    Build a complete two-motif SequenceDesign.

    Supported architectures
    -----------------------
    Alternating
    Even distribution
    Diblock
    Triblock A-B-A
    Triblock B-A-B
    Block pattern
    """

    validate_two_motif_inputs(
        motif_a=motif_a,
        count_a=count_a,
        motif_b=motif_b,
        count_b=count_b,
        motifs=motifs,
    )

    if block_size_b is None:
        block_size_b = (
            block_size_a
        )

    # --------------------------------------------------------
    # Architecture selection
    # --------------------------------------------------------

    if architecture == "Alternating":

        motif_order = (
            build_alternating_order(
                motif_a=motif_a,
                count_a=count_a,
                motif_b=motif_b,
                count_b=count_b,
            )
        )

    elif architecture == "Even distribution":

        motif_order = (
            build_evenly_distributed_order(
                motif_a=motif_a,
                count_a=count_a,
                motif_b=motif_b,
                count_b=count_b,
            )
        )

    elif architecture == "Diblock":

        motif_order = (
            build_diblock_order(
                motif_a=motif_a,
                count_a=count_a,
                motif_b=motif_b,
                count_b=count_b,
            )
        )

    elif architecture == "Triblock A-B-A":

        motif_order = (
            build_triblock_order(
                motif_a=motif_a,
                count_a=count_a,
                motif_b=motif_b,
                count_b=count_b,
            )
        )

    elif architecture == "Triblock B-A-B":

        motif_order = (
            build_inverse_triblock_order(
                motif_a=motif_a,
                count_a=count_a,
                motif_b=motif_b,
                count_b=count_b,
            )
        )

    elif architecture == "Block pattern":

        motif_order = (
            build_block_pattern_order(
                motif_a=motif_a,
                count_a=count_a,
                motif_b=motif_b,
                count_b=count_b,
                block_size_a=block_size_a,
                block_size_b=block_size_b,
            )
        )

    else:

        raise ValueError(
            f"Unknown architecture: '{architecture}'"
        )

    # --------------------------------------------------------
    # Return complete design
    # --------------------------------------------------------

    return create_design(
        motif_order=motif_order,
        motifs=motifs,
    )


# ============================================================
# Manual/custom motif order
# ============================================================

def build_custom_design(
    motif_order: list[str],
    motifs: dict[str, Motif],
) -> SequenceDesign:
    """
    Create a design from an explicitly supplied motif order.

    This will later be useful for drag-and-drop/manual
    architecture editing in the graphical interface.
    """

    if not motif_order:
        raise ValueError(
            "Custom motif order cannot be empty."
        )

    return create_design(
        motif_order=motif_order,
        motifs=motifs,
    )


# ============================================================
# Standalone test
# ============================================================

if __name__ == "__main__":

    from .motifs import get_default_motifs

    motifs = (
        get_default_motifs()
    )

    design = (
        build_two_motif_design(
            motif_a="VPGVG",
            count_a=8,
            motif_b="IPAVG",
            count_b=4,
            architecture="Even distribution",
            motifs=motifs,
        )
    )

    print(
        "Motif order:"
    )

    print(
        design.motif_order
    )

    print()

    print(
        "Sequence:"
    )

    print(
        design.sequence
    )

    print()

    print(
        f"Total motifs: "
        f"{design.total_motifs}"
    )

    print(
        f"Total AA: "
        f"{design.total_aa}"
    )

    print(
        "Counts:",
        design.motif_counts,
    )
