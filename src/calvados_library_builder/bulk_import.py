"""Import simulation-ready multi-record FASTA or name/sequence CSV libraries."""
from __future__ import annotations

import csv
import io
import re

from .designs import Candidate, validate_sequence

MAX_LIBRARY_SIZE = 1000
MAX_TOTAL_AA = 1_000_000


def _safe_name(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw.strip()).strip("._")
    if not cleaned:
        raise ValueError("Every imported sequence needs a non-empty name.")
    return cleaned


def parse_sequence_library(text: str, *, filename: str = "library.fasta") -> list[Candidate]:
    """Parse a multi-FASTA or CSV containing 'name' and 'sequence' columns.

    No sequence is silently dropped. Duplicate normalized names are rejected,
    rather than overwriting or accidentally preparing two runs to the same path.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Library file or pasted text is empty.")
    records: list[tuple[str, str]] = []
    if filename.lower().endswith(".csv"):
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
        fields = {f.strip().lower(): f for f in reader.fieldnames or []}
        name_col = fields.get("name") or fields.get("id") or fields.get("sequence_name")
        seq_col = fields.get("sequence") or fields.get("amino_acid_sequence")
        if not name_col or not seq_col:
            raise ValueError("CSV must have name (or id) and sequence columns.")
        for number, row in enumerate(reader, start=2):
            if row is None or None in row:
                raise ValueError(f"Malformed CSV record on line {number}.")
            records.append((row.get(name_col, "") or "", row.get(seq_col, "") or ""))
    else:
        name: str | None = None
        sequence: list[str] = []
        for number, line in enumerate(text.lstrip("\ufeff").splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(">"):
                if name is not None:
                    records.append((name, "".join(sequence)))
                name = stripped[1:].split()[0] if stripped[1:].strip() else ""
                sequence = []
            elif name is None:
                raise ValueError(
                    f"Expected a FASTA header beginning with '>' before line {number}."
                )
            else:
                sequence.append(stripped)
        if name is not None:
            records.append((name, "".join(sequence)))

    if not records:
        raise ValueError("No sequences found. Use multi-FASTA or CSV.")
    if len(records) > MAX_LIBRARY_SIZE:
        raise ValueError(f"Maximum library size is {MAX_LIBRARY_SIZE} sequences.")
    result: list[Candidate] = []
    seen: set[str] = set()
    total_aa = 0
    for index, (name, sequence) in enumerate(records, start=1):
        clean_name = _safe_name(name)
        if clean_name.casefold() in seen:
            raise ValueError(f"Duplicate sequence name after normalization: {clean_name}")
        seen.add(clean_name.casefold())
        try:
            aa = validate_sequence(sequence)
        except ValueError as exc:
            raise ValueError(f"Sequence {index} ({clean_name}): {exc}") from exc
        total_aa += len(aa)
        if total_aa > MAX_TOTAL_AA:
            raise ValueError(f"Combined library exceeds {MAX_TOTAL_AA:,} amino acids.")
        result.append(Candidate(clean_name, aa, "imported sequence"))
    return result
