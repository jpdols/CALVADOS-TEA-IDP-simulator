"""Portable native Streamlit architecture editor.

The previously committed drag-and-drop component source was truncated before its
CSS, JavaScript and Python entry points. This provides a functional editor on
all Streamlit 1.x installations without an external frontend build.
"""
from __future__ import annotations

from collections import Counter

import streamlit as st

from .motifs import Motif
from .sequences import SequenceDesign


def motif_order_to_blocks(motif_order: list[str]) -> list[dict]:
    blocks: list[dict] = []
    for motif in motif_order:
        if blocks and blocks[-1]["motif"] == motif:
            blocks[-1]["count"] += 1
        else:
            blocks.append({"motif": motif, "count": 1})
    return blocks


def blocks_to_motif_order(blocks: list[dict]) -> list[str]:
    return [block["motif"] for block in blocks for _ in range(block["count"])]


def design_to_blocks(design: SequenceDesign) -> list[dict]:
    return motif_order_to_blocks(design.motif_order)


def sanitize_blocks(blocks: list[dict] | None, motifs: dict[str, Motif]) -> list[dict]:
    clean: list[dict] = []
    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        motif = str(block.get("motif", ""))
        if motif not in motifs:
            continue
        try:
            count = int(block.get("count", 1))
        except (TypeError, ValueError):
            count = 1
        clean.append({"motif": motif, "count": max(1, min(count, 100_000))})
    return clean


def blocks_to_design(blocks: list[dict], motifs: dict[str, Motif]) -> SequenceDesign:
    clean = sanitize_blocks(blocks, motifs)
    order = blocks_to_motif_order(clean)
    return SequenceDesign(
        motif_order=order,
        sequence="".join(motifs[name].sequence for name in order),
        motif_counts=dict(Counter(order)),
    )


def get_block_statistics(blocks: list[dict], motifs: dict[str, Motif]) -> dict:
    clean = sanitize_blocks(blocks, motifs)
    counts = Counter()
    for block in clean:
        counts[block["motif"]] += block["count"]
    return {
        "blocks": len(clean),
        "total_motifs": sum(counts.values()),
        "total_aa": sum(count * len(motifs[name].sequence) for name, count in counts.items()),
        "motif_counts": dict(counts),
    }


def architecture_editor(
    blocks: list[dict],
    motifs: dict[str, Motif],
    key: str = "architecture_editor",
) -> list[dict]:
    """Edit counts, motifs, ordering, splitting and deleting without custom JS.

    Changes update the returned architecture on the next Streamlit rerun.
    External changes use a revised key, as provided by app.py.
    """
    current = sanitize_blocks(blocks, motifs)
    st.caption("Edit motif blocks below. Use arrows to reorder or Split to divide a block.")
    output: list[dict] = []
    move_up: int | None = None
    move_down: int | None = None
    remove: int | None = None
    split: int | None = None

    for i, block in enumerate(current):
        with st.container(border=True):
            st.markdown(f"**Block {i + 1}**")
            motif_col, count_col = st.columns([2, 1])
            with motif_col:
                names = list(motifs)
                motif = st.selectbox(
                    "Motif", names, index=names.index(block["motif"]),
                    key=f"{key}_motif_{i}",
                )
            with count_col:
                count = st.number_input(
                    "Repeats", min_value=1, max_value=100_000,
                    value=block["count"], step=1, key=f"{key}_count_{i}",
                )
            output.append({"motif": motif, "count": int(count)})
            up, down, halve, delete = st.columns(4)
            with up:
                if st.button("↑ Up", key=f"{key}_up_{i}", disabled=i == 0):
                    move_up = i
            with down:
                if st.button("↓ Down", key=f"{key}_down_{i}", disabled=i == len(current) - 1):
                    move_down = i
            with halve:
                if st.button("Split", key=f"{key}_split_{i}", disabled=count < 2):
                    split = i
            with delete:
                if st.button("Delete", key=f"{key}_delete_{i}"):
                    remove = i

    if move_up is not None:
        output[move_up - 1], output[move_up] = output[move_up], output[move_up - 1]
    elif move_down is not None:
        output[move_down], output[move_down + 1] = output[move_down + 1], output[move_down]
    elif remove is not None:
        output.pop(remove)
    elif split is not None:
        original = output.pop(split)
        first = original["count"] // 2
        output[split:split] = [
            {"motif": original["motif"], "count": first},
            {"motif": original["motif"], "count": original["count"] - first},
        ]

    # Widget values persist under their keys. After a structural change,
    # invalidate keys and rerun to avoid applying the old row values to
    # newly moved, split or deleted rows.
    if any(value is not None for value in (move_up, move_down, remove, split)):
        st.session_state["architecture_blocks"] = output
        st.session_state["architecture_revision"] = (
            st.session_state.get("architecture_revision", 0) + 1
        )
        st.rerun()

    return output
