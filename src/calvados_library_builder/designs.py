"""Pure sequence-design helpers for single ELPs and small libraries."""
from __future__ import annotations

import random
import re
from dataclasses import dataclass

VALID_AA = frozenset("ACDEFGHIKLMNPQRSTVWY")


@dataclass(frozen=True)
class Candidate:
    name: str
    sequence: str
    architecture: str


def validate_sequence(sequence: str) -> str:
    cleaned = re.sub(r"\\s+", "", sequence).upper()
    if not cleaned or (set(cleaned) - VALID_AA):
        raise ValueError("Sequence must contain only the 20 standard one-letter amino acids.")
    return cleaned


def simple_elp(name: str, motif: str, repeats: int) -> Candidate:
    motif = validate_sequence(motif)
    if not 1 <= repeats <= 5000:
        raise ValueError("Repeats must be between 1 and 5000.")
    return Candidate(name, motif * repeats, f"{motif} × {repeats}")


def make_library(
    prefix: str, motif_a: str, motif_b: str, total_motifs: int,
    fractions_b: list[float], architectures: list[str], seed: int = 1,
) -> list[Candidate]:
    """Create deterministic composition-matched variants for each B fraction.

    Valid architectures: alternating, diblock, central, shuffled.
    For unequal ratios, alternating distributes B motifs through the
    sequence with nearest-integer spacing; it is not necessarily strict ABAB.
    """
    motif_a = validate_sequence(motif_a)
    motif_b = validate_sequence(motif_b)
    if motif_a == motif_b:
        raise ValueError("Library motifs must be different.")
    if not 2 <= total_motifs <= 5000:
        raise ValueError("Total motifs must be between 2 and 5000.")
    choices = {"alternating", "diblock", "central", "shuffled"}
    if not architectures or any(a not in choices for a in architectures):
        raise ValueError(f"Select architectures among {sorted(choices)}.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", prefix):
        raise ValueError("Library name must contain only letters, digits, _, - or .")
    results: list[Candidate] = []
    seen: set[str] = set()
    for fraction in fractions_b:
        if not 0 <= fraction <= 1:
            raise ValueError("Fractions must be between 0 and 1.")
        nb = round(total_motifs * fraction)
        na = total_motifs - nb
        composition = f"B{nb:03d}"
        for arch in architectures:
            if arch == "diblock":
                order = [motif_a] * na + [motif_b] * nb
            elif arch == "central":
                left = na // 2
                order = [motif_a] * left + [motif_b] * nb + [motif_a] * (na - left)
            elif arch == "alternating":
                order = [motif_b if ((i + 1) * nb // total_motifs) >
                         (i * nb // total_motifs) else motif_a
                         for i in range(total_motifs)]
            else:
                order = [motif_a] * na + [motif_b] * nb
                random.Random(f"{seed}-{composition}-{motif_a}-{motif_b}").shuffle(order)
            name = f"{prefix}_{composition}_{arch}"
            if name not in seen:
                results.append(Candidate(name, "".join(order), arch))
                seen.add(name)
    return results
