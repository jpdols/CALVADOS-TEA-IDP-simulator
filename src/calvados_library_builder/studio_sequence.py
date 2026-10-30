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
    """Canonicalize single-motif runs and explicitly grouped architecture units.

    A manual group is one ordered *unit* with an integer repetition count.
    For example, [{A×2}, {B×1}] repeated three times means AAB AAB AAB.
    Unlike ordinary mono-motif runs, manual group boundaries never merge.
    Legacy multi-segment groups are retained and treated as one manual unit.
    """
    if not isinstance(groups, list) or len(groups) > MAX_GROUPS:
        raise ValueError(f"Expected a list of at most {MAX_GROUPS} blocks.")
    output: list[dict] = []
    residues = 0
    for index, group in enumerate(groups):
        if not isinstance(group, dict) or not isinstance(group.get("segments"), list):
            raise ValueError(f"Invalid motif block {index + 1}.")
        raw_repeat = group.get("repeat", 1)
        if isinstance(raw_repeat, bool) or not isinstance(raw_repeat, int) or not 1 <= raw_repeat <= 5000:
            raise ValueError("Group repeat count must be an integer between 1 and 5000.")
        parts: list[dict] = []
        for segment in group["segments"]:
            if not isinstance(segment, dict):
                raise ValueError("Invalid motif segment.")
            name, count = segment.get("motif"), segment.get("count")
            if not isinstance(name, str) or name not in motifs:
                raise ValueError(f"Unknown motif in sequence: {name!r}")
            if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 5000:
                raise ValueError("Motif count must be an integer between 1 and 5000.")
            if parts and parts[-1]["motif"] == name and parts[-1]["count"] + count <= 5000:
                parts[-1]["count"] += count
            else:
                parts.append({"motif": name, "count": count})
        if not parts:
            continue
        residues += sum(len(motifs[p["motif"]].sequence) * p["count"] for p in parts) * raw_repeat
        if residues > MAX_RESIDUES:
            raise ValueError(f"Maximum sequence length is {MAX_RESIDUES:,} residues.")
        manual = bool(group.get("manual", False)) or len(parts) > 1
        split = bool(group.get("split_before", False))
        if not manual and raw_repeat == 1:
            p = parts[0]
            if (
                output and not output[-1].get("manual")
                and output[-1]["segments"][0]["motif"] == p["motif"]
                and not split
                and output[-1]["segments"][0]["count"] + p["count"] <= 5000
            ):
                output[-1]["segments"][0]["count"] += p["count"]
                continue
            block = {"segments": [p]}
            if split and output:
                block["split_before"] = True
            output.append(block)
        else:
            output.append({
                "segments": parts,
                "repeat": raw_repeat,
                "manual": True,
            })
    if len(output) > MAX_GROUPS:
        raise ValueError(f"Maximum number of motif blocks is {MAX_GROUPS}.")
    return output


def groups_to_sequence(groups: object, motifs: Mapping[str, Motif]) -> str:
    return "".join(
        "".join(motifs[part["motif"]].sequence * part["count"]
                for part in group["segments"]) * group.get("repeat", 1)
        for group in normalize_groups(groups, motifs)
    )


def groups_to_architecture(groups: object, motifs: Mapping[str, Motif]) -> str:
    descriptions: list[str] = []
    for group in normalize_groups(groups, motifs):
        parts = " + ".join(
            f'{part["motif"]}×{part["count"]}' for part in group["segments"]
        )
        if group.get("manual"):
            descriptions.append(f"({parts})×{group.get('repeat', 1)}")
        else:
            descriptions.append(parts)
    return " | ".join(descriptions)


def count_motifs(groups: object, motifs: Mapping[str, Motif]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for group in normalize_groups(groups, motifs):
        repeat = group.get("repeat", 1)
        for part in group["segments"]:
            name = part["motif"]
            counts[name] = counts.get(name, 0) + part["count"] * repeat
    return counts


def make_manual_group(groups: object, first: int, last: int,
                      motifs: Mapping[str, Motif]) -> list[dict]:
    """Group consecutive blocks into a repeatable ordered unit.

    If an existing group is selected, materialize its copies first so
    grouping preserves the exact concatenated amino-acid sequence.
    """
    canonical = normalize_groups(groups, motifs)
    if not (0 <= first < last < len(canonical)):
        raise ValueError("Select at least two adjacent blocks to group.")
    selected = canonical[first:last + 1]
    parts: list[dict] = []
    for block in selected:
        for _ in range(block.get("repeat", 1)):
            for part in block["segments"]:
                if parts and parts[-1]["motif"] == part["motif"] and parts[-1]["count"] + part["count"] <= 5000:
                    parts[-1]["count"] += part["count"]
                else:
                    parts.append(dict(part))
    new = canonical[:first] + [{"segments": parts, "repeat": 1, "manual": True}] + canonical[last + 1:]
    return normalize_groups(new, motifs)


def set_group_repeats(groups: object, index: int, repeats: int,
                      motifs: Mapping[str, Motif]) -> list[dict]:
    canonical = normalize_groups(groups, motifs)
    if not 0 <= index < len(canonical):
        raise IndexError(index)
    if not isinstance(repeats, int) or isinstance(repeats, bool) or not 1 <= repeats <= 5000:
        raise ValueError("Repetitions must be between 1 and 5000.")
    block = canonical[index]
    if block.get("manual"):
        block["repeat"] = repeats
    else:
        block["segments"][0]["count"] = repeats
    return normalize_groups(canonical, motifs)


def ungroup_manual_block(groups: object, index: int,
                         motifs: Mapping[str, Motif]) -> list[dict]:
    canonical = normalize_groups(groups, motifs)
    if not 0 <= index < len(canonical):
        raise IndexError(index)
    block = canonical[index]
    if not block.get("manual"):
        return canonical
    expanded = [
        {"segments": [dict(part)], "split_before": True}
        for _ in range(block.get("repeat", 1)) for part in block["segments"]
    ]
    return normalize_groups(canonical[:index] + expanded + canonical[index + 1:], motifs)


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
