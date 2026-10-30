"""Sequence groups and persistent custom motif library, independent of Streamlit."""
from __future__ import annotations

import json
import re
import shutil
from collections.abc import Mapping
from pathlib import Path

from .motifs import Motif, create_motif, get_default_motifs, validate_motif_sequence

MAX_GROUPS = 2000
MAX_RESIDUES = 50000
MAX_MOTIFS = 200
FRAGMENT_COLOR = "#9CA3AF"


def default_groups() -> list[dict]:
    return [{"segments": [{"motif": "VPGVG", "count": 10}]}]


def normalize_groups(groups: object, motifs: Mapping[str, Motif]) -> list[dict]:
    """Return contiguous single-motif runs, merging identical neighbors.

    An explicit split is represented by split_before=True on the second run.
    It preserves two draggable portions of the same motif until either moves;
    all other neighboring identical runs are automatically merged. Legacy
    multi-motif groups are expanded without losing their amino-acid order.
    """
    if not isinstance(groups, list) or len(groups) > MAX_GROUPS:
        raise ValueError(f"Expected a list of at most {MAX_GROUPS} groups.")
    output: list[dict] = []
    residues = 0
    for index, group in enumerate(groups):
        if not isinstance(group, dict) or not isinstance(group.get("segments"), list):
            raise ValueError(f"Invalid group {index + 1}.")
        for j, segment in enumerate(group["segments"]):
            if not isinstance(segment, dict):
                raise ValueError("Invalid motif segment.")
            name, count = segment.get("motif"), segment.get("count")
            if not isinstance(name, str) or name not in motifs:
                raise ValueError(f"Unknown motif in sequence: {name!r}")
            if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 5000:
                raise ValueError("Repeat count must be an integer between 1 and 5000.")
            residues += len(motifs[name].sequence) * count
            if residues > MAX_RESIDUES:
                raise ValueError(f"Maximum sequence length is {MAX_RESIDUES:,} residues.")
            split = bool(group.get("split_before", False)) and j == 0
            if output and output[-1]["segments"][0]["motif"] == name and not split:
                merged = output[-1]["segments"][0]["count"] + count
                if merged <= 5000:
                    output[-1]["segments"][0]["count"] = merged
                    continue
            entry = {"segments": [{"motif": name, "count": count}]}
            if split and output:
                entry["split_before"] = True
            output.append(entry)
    if len(output) > MAX_GROUPS:
        raise ValueError(f"Maximum number of motif blocks is {MAX_GROUPS}.")
    return output


def groups_to_sequence(groups: object, motifs: Mapping[str, Motif]) -> str:
    return "".join(
        motifs[item["motif"]].sequence * item["count"]
        for group in normalize_groups(groups, motifs)
        for item in group["segments"]
    )


def groups_to_architecture(groups: object, motifs: Mapping[str, Motif]) -> str:
    return " | ".join(
        f'{group["segments"][0]["motif"]}×{group["segments"][0]["count"]}'
        for group in normalize_groups(groups, motifs)
    )


def count_motifs(groups: object, motifs: Mapping[str, Motif]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for group in normalize_groups(groups, motifs):
        part = group["segments"][0]
        name = part["motif"]
        counts[name] = counts.get(name, 0) + part["count"]
    return counts


def _write_saved_json(path: Path, payload: object) -> None:
    """Persist safely, with a fallback for Windows external-drive renames."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        temp.replace(path)
    except (PermissionError, FileExistsError):
        # Some drives cannot rename over an existing file; retain an old
        # backup then copy the new JSON directly instead of losing edits.
        if path.is_file():
            shutil.copyfile(path, path.with_name(path.name + ".previous"))
        shutil.copyfile(temp, path)
        temp.unlink(missing_ok=True)


def load_draft(path: Path, motifs: Mapping[str, Motif]) -> tuple[str, list[dict]]:
    """Load a saved design. Corrupted drafts raise instead of silently erasing."""
    if not path.is_file():
        return "test_sequence", default_groups()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Unsupported saved sequence draft format.")
    name = data.get("name", "test_sequence")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Invalid sequence name in draft.")
    return name, normalize_groups(data.get("groups"), motifs)


def save_draft(
    path: Path, name: str, groups: object, motifs: Mapping[str, Motif]
) -> None:
    """Store exact ordered blocks locally for the next application session."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Sequence name cannot be empty.")
    normalized = normalize_groups(groups, motifs)
    payload = {"version": 1, "name": name, "groups": normalized}
    _write_saved_json(path, payload)


def extract_single_fasta(text: str) -> str:
    """Accept bare AA sequence or a one-record FASTA; reject multi-record FASTA."""
    lines = text.splitlines()
    headers = [line for line in lines if line.lstrip().startswith(">")]
    if len(headers) > 1:
        raise ValueError("Paste one FASTA record at a time.")
    clean = re.sub(r"\s+", "", "".join(
        line for line in lines if not line.lstrip().startswith(">")
    )).upper()
    validate_motif_sequence(clean)
    if len(clean) > MAX_RESIDUES:
        raise ValueError(f"Maximum sequence length is {MAX_RESIDUES:,} residues.")
    return clean


def segment_raw_sequence(
    sequence: str, motifs: Mapping[str, Motif]
) -> tuple[list[dict], dict[str, Motif]]:
    """Find longest matching known motifs and preserve all unmatched residues.

    Unmatched consecutive residues become a new grey fragment motif, so
    sequence import is lossless even if a motif is not in the palette.
    """
    sequence = extract_single_fasta(sequence)
    motifs = dict(motifs)
    motif_choices = sorted(
        (m for m in motifs.values() if m.sequence),
        key=lambda m: (-len(m.sequence), m.name),
    )
    groups: list[dict] = []
    extra: dict[str, Motif] = {}
    pending: list[str] = []
    pos = 0

    def flush_unmatched() -> None:
        if not pending:
            return
        idx = 1
        while f"FRAGMENT_{idx:03d}" in motifs or f"FRAGMENT_{idx:03d}" in extra:
            idx += 1
        name = f"FRAGMENT_{idx:03d}"
        fragment = create_motif(name, "".join(pending), FRAGMENT_COLOR, label="Unmatched")
        extra[name] = fragment
        groups.append({"segments": [{"motif": name, "count": 1}]})
        pending.clear()

    while pos < len(sequence):
        match = next(
            (m for m in motif_choices if sequence.startswith(m.sequence, pos)), None
        )
        if match is None:
            pending.append(sequence[pos])
            pos += 1
            continue
        flush_unmatched()
        if groups and len(groups[-1]["segments"]) == 1 and (
            groups[-1]["segments"][0]["motif"] == match.name
        ):
            groups[-1]["segments"][0]["count"] += 1
        else:
            groups.append({"segments": [{"motif": match.name, "count": 1}]})
        pos += len(match.sequence)
    flush_unmatched()
    return groups, extra


def load_custom_motifs(path: Path) -> dict[str, Motif]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) > MAX_MOTIFS:
        raise ValueError("Invalid saved motif library.")
    defaults = get_default_motifs()
    result: dict[str, Motif] = {}
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Invalid motif record.")
        motif = create_motif(
            item["name"], item["sequence"], item["color"], item.get("label")
        )
        if motif.name in defaults or motif.name in result:
            raise ValueError(f"Duplicate or reserved motif name: {motif.name}")
        result[motif.name] = motif
    return result


def save_custom_motifs(path: Path, custom: Mapping[str, Motif]) -> None:
    if len(custom) > MAX_MOTIFS:
        raise ValueError(f"Maximum of {MAX_MOTIFS} custom motifs.")
    defaults = get_default_motifs()
    payload = []
    for motif in custom.values():
        if motif.name in defaults:
            raise ValueError(f"Cannot override thesis motif colors: {motif.name}")
        payload.append({
            "name": motif.name,
            "sequence": motif.sequence,
            "color": motif.color,
            "label": motif.label,
        })
    _write_saved_json(path, payload)
