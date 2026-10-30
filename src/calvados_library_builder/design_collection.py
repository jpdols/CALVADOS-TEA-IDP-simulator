"""Persistent collection of ELP/IDP designs awaiting simulation preparation.

Designs are sequence snapshots. Editing the canvas after staging a design
will not silently change the sequence previously added to the collection.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from .designs import Candidate, validate_sequence
from .studio_sequence import _write_saved_json

MAX_DESIGNS = 1000
MAX_SEQUENCE_LENGTH = 50000
MAX_TOTAL_RESIDUES = 1_000_000
_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")


def _checked_candidate(candidate: Candidate) -> Candidate:
    if not isinstance(candidate, Candidate):
        raise ValueError("Invalid design in collection.")
    if not _NAME_RE.fullmatch(candidate.name) or candidate.name.endswith("."):
        raise ValueError(f"Invalid design name: {candidate.name!r}. Use letters, numbers, _, - or .")
    try:
        sequence = validate_sequence(candidate.sequence)
    except ValueError as exc:
        raise ValueError(f"{candidate.name}: {exc}") from exc
    if len(sequence) > MAX_SEQUENCE_LENGTH:
        raise ValueError(f"{candidate.name} exceeds {MAX_SEQUENCE_LENGTH:,} amino acids.")
    if not isinstance(candidate.architecture, str):
        raise ValueError(f"{candidate.name} has an invalid architecture label.")
    return Candidate(candidate.name, sequence, candidate.architecture)


def add_to_collection(
    existing: Iterable[Candidate],
    designs: Iterable[Candidate],
) -> list[Candidate]:
    """Append all-or-nothing, preserve insertion order, reject duplicate names."""
    existing_list = list(existing)
    additions = list(designs)
    if not additions:
        raise ValueError("No designs selected to add.")
    combined = [_checked_candidate(c) for c in (*existing_list, *additions)]
    if len(combined) > MAX_DESIGNS:
        raise ValueError(f"The collection cannot exceed {MAX_DESIGNS:,} designs.")
    seen: set[str] = set()
    for candidate in combined:
        name_key = candidate.name.casefold()
        if name_key in seen:
            raise ValueError(
                f"{candidate.name!r} is already in the collection. "
                "Give the new design a different name."
            )
        seen.add(name_key)
    if sum(len(c.sequence) for c in combined) > MAX_TOTAL_RESIDUES:
        raise ValueError(f"The collection exceeds {MAX_TOTAL_RESIDUES:,} amino acids.")
    return combined


def remove_from_collection(existing: Iterable[Candidate], name: str) -> list[Candidate]:
    original = list(existing)
    filtered = [c for c in original if c.name.casefold() != name.casefold()]
    if len(filtered) == len(original):
        raise ValueError(f"Design not found in collection: {name}")
    return filtered


def next_design_name(existing: Iterable[Candidate]) -> str:
    names = {c.name.casefold() for c in existing}
    i = 1
    while f"ELP_{i:02d}".casefold() in names:
        i += 1
    return f"ELP_{i:02d}"


def save_collection(path: Path, designs: Iterable[Candidate]) -> None:
    checked = [_checked_candidate(c) for c in designs]
    # Validate all names and limits before touching the saved collection.
    if checked:
        checked = add_to_collection([], checked)
    _write_saved_json(Path(path), {
        "version": 1,
        "designs": [
            {"name": c.name, "sequence": c.sequence, "architecture": c.architecture}
            for c in checked
        ],
    })


def load_collection(path: Path) -> list[Candidate]:
    path = Path(path)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Unsupported saved design collection format.")
    designs = data.get("designs")
    if not isinstance(designs, list):
        raise ValueError("Invalid saved design collection.")
    checked = []
    for entry in designs:
        if not isinstance(entry, dict):
            raise ValueError("Invalid design entry in saved collection.")
        checked.append(Candidate(
            name=entry.get("name"),
            sequence=entry.get("sequence"),
            architecture=entry.get("architecture", ""),
        ))
    return add_to_collection([], checked) if checked else []
