#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from collections import Counter
from typing import Callable

import streamlit as st

from .motifs import Motif
from .sequences import SequenceDesign


# ============================================================
# Python helpers
# ============================================================

def motif_order_to_blocks(
    motif_order: list[str],
) -> list[dict]:
    """
    Collapse a motif-by-motif architecture into contiguous
    blocks.
    """

    if not motif_order:
        return []

    blocks: list[dict] = []

    current_motif = motif_order[0]
    current_count = 1

    for motif_name in motif_order[1:]:

        if motif_name == current_motif:

            current_count += 1

        else:

            blocks.append(
                {
                    "motif": current_motif,
                    "count": current_count,
                }
            )

            current_motif = motif_name
            current_count = 1

    blocks.append(
        {
            "motif": current_motif,
            "count": current_count,
        }
    )

    return blocks


def blocks_to_motif_order(
    blocks: list[dict],
) -> list[str]:

    motif_order: list[str] = []

    for block in blocks:

        motif_name = str(
            block["motif"]
        )

        count = int(
            block["count"]
        )

        motif_order.extend(
            [motif_name] * count
        )

    return motif_order


def design_to_blocks(
    design: SequenceDesign,
) -> list[dict]:

    return motif_order_to_blocks(
        design.motif_order
    )


def sanitize_blocks(
    blocks: list[dict] | None,
    motifs: dict[str, Motif],
) -> list[dict]:

    if not blocks:
        return []

    clean_blocks: list[dict] = []

    for block in blocks:

        if not isinstance(
            block,
            dict,
        ):
            continue

        motif_name = str(
            block.get(
                "motif",
                "",
            )
        )

        if motif_name not in motifs:
            continue

        try:

            count = int(
                block.get(
                    "count",
                    1,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            count = 1

        count = max(
            1,
            min(
                count,
                100_000,
            ),
        )

        clean_blocks.append(
            {
                "motif": motif_name,
                "count": count,
            }
        )

    return clean_blocks


def blocks_to_design(
    blocks: list[dict],
    motifs: dict[str, Motif],
) -> SequenceDesign:

    clean_blocks = sanitize_blocks(
        blocks=blocks,
        motifs=motifs,
    )

    motif_order = blocks_to_motif_order(
        clean_blocks
    )

    sequence = "".join(
        motifs[
            motif_name
        ].sequence
        for motif_name in motif_order
    )

    motif_counts = dict(
        Counter(
            motif_order
        )
    )

    return SequenceDesign(
        motif_order=motif_order,
        sequence=sequence,
        motif_counts=motif_counts,
    )


# ============================================================
# HTML
# ============================================================

EDITOR_HTML = """
<div class="ae-root">

    <div class="ae-toolbar">

        <div class="ae-toolbar-text">

            <strong>
                Architecture editor
            </strong>

            <span class="ae-toolbar-help">
                Drag = move · click = edit · double-click = split
            </span>

        </div>

        <div
            class="ae-total"
            aria-live="polite"
        ></div>

    </div>


    <div
        class="ae-blocks"
        role="list"
        aria-label="Sequence architecture blocks"
    ></div>


    <div class="ae-inspector">

        <div class="ae-empty-inspector">

            <strong>
                Select a block
            </strong>

            <span>
                Click to edit, double-click for a quick
                half split, or drag to reorder.
            </span>

        </div>


        <div
            class="ae-editor"
            hidden
        >

            <div class="ae-editor-header">

                <div>

                    <div class="ae-editor-title">
                        Block
                    </div>

                    <div class="ae-editor-meta">
                    </div>

                </div>

                <button
                    class="ae-close"
                    type="button"
                    aria-label="Close block editor"
                >
                    ×
                </button>

            </div>


            <div class="ae-editor-grid">

                <label class="ae-field">

                    <span>
                        Motif
                    </span>

                    <select
                        class="ae-motif-select"
                    ></select>

                </label>


                <label class="ae-field">

                    <span>
                        Number of motifs
                    </span>

                    <div class="ae-number-control">

                        <button
                            class="ae-count-minus"
                            type="button"
                            aria-label="Decrease motif count"
                        >
                            −
                        </button>

                        <input
                            class="ae-count-input"
                            type="number"
                            min="1"
                            step="1"
                        />

                        <button
                            class="ae-count-plus"
                            type="button"
                            aria-label="Increase motif count"
                        >
                            +
                        </button>

                    </div>

                </label>

            </div>


            <div class="ae-actions-row">

                <button
                    class="ae-move-left"
                    type="button"
                >
                    ← Move left
                </button>

                <button
                    class="ae-move-right"
                    type="button"
                >
                    Move right →
                </button>

                <button
                    class="ae-delete"
                    type="button"
                >
                    Delete block
                </button>

            </div>


            <div
                class="ae-split-panel"
                hidden
            >

                <div class="ae-divider"></div>


                <div class="ae-split-heading">

                    <div>

                        <strong>
                            Split block
                        </strong>

                        <span class="ae-split-description">
                            Choose the left size. The right
                            block is calculated automatically.
                        </span>

                    </div>

                </div>


                <div class="ae-split-controls">

                    <label class="ae-field">

                        <span>
                            Left block
                        </span>

                        <input
                            class="ae-split-left"
                            type="number"
                            min="1"
                            step="1"
                        />

                    </label>


                    <div class="ae-split-plus">
                        +
                    </div>


                    <label class="ae-field">

                        <span>
                            Right block
                        </span>

                        <input
                            class="ae-split-right"
                            type="number"
                            min="1"
                            step="1"
                            disabled
                        />

                    </label>


                    <button
                        class="ae-split-button"
                        type="button"
                    >
                        Split
                    </button>

                </div>

            </div>

        </div>

    </div>


    <div
        class="ae-message"
        aria-live="polite"
    ></div>

</div>
"""


# ============================================================
# CSS
# ============================================================

EDITOR_CSS = """
.ae-root {
    width: 100%;
    box-sizing: border-box;

    font-family:
        var(--st-font),
        system-ui,
        sans-serif;

    color:
        var(--st-text-color);
}


/* ==========================================================
   Toolbar
   ========================================================== */

.ae-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;

    flex-wrap: wrap;

    gap: 8px 20px;

    margin-bottom: 10px;
}

.ae-toolbar-text {
    display: flex;
    flex-direction: column;

    gap: 2px;
}

.ae-toolbar-help {
    font-size: 0.78rem;
    opacity: 0.62;
}

.ae-total {
    font-size: 0.78rem;
    opacity: 0.72;
}


/* ==========================================================
   Architecture
   ========================================================== */

.ae-blocks {
    display: flex;
    flex-wrap: wrap;

    align-items: center;

    gap: 13px;

    min-height: 68px;

    padding: 17px 16px;

    border:
        1px solid
        rgba(128, 128, 128, 0.20);

    border-radius: 10px;

    background:
        rgba(128, 128, 128, 0.035);

    box-sizing: border-box;
}


/* ==========================================================
   Ball
   ========================================================== */

.ae-block-wrapper {
    position: relative;

    display: inline-flex;

    align-items: center;
    justify-content: center;

    width: 38px;
    height: 38px;

    flex: 0 0 38px;
}

.ae-block {
    position: relative;

    width: 31px;
    height: 31px;

    border-radius: 50%;

    border:
        1px solid
        rgba(0, 0, 0, 0.20);

    padding: 0;

    cursor: grab;

    outline: none;

    transition:
        transform 0.10s ease,
        box-shadow 0.10s ease,
        border-color 0.10s ease,
        opacity 0.10s ease;

    box-sizing: border-box;
}

.ae-block:active {
    cursor: grabbing;
}

.ae-block:hover {
    transform: scale(1.08);
}

.ae-block:focus-visible {
    box-shadow:
        0 0 0 3px
        var(--st-primary-color);
}

.ae-block.ae-selected {
    border:
        3px solid
        var(--st-primary-color);

    transform:
        scale(1.08);
}

.ae-block.ae-dragging {
    opacity: 0.35;
}

.ae-block.ae-drop-target {
    box-shadow:
        0 0 0 3px
        var(--st-primary-color);
}


/* ==========================================================
   Count
   ========================================================== */

.ae-count-badge {
    position: absolute;

    right: -6px;
    bottom: -5px;

    min-width: 16px;
    height: 16px;

    padding: 0 4px;

    display: flex;

    justify-content: center;
    align-items: center;

    border-radius: 9px;

    background:
        var(--st-background-color);

    color:
        var(--st-text-color);

    border:
        1px solid
        rgba(128, 128, 128, 0.38);

    font-size: 9px;
    font-weight: 700;

    line-height: 1;

    pointer-events: none;

    box-sizing: border-box;
}


/* ==========================================================
   Tooltip
   ========================================================== */

.ae-tooltip {
    display: none;

    position: absolute;

    z-index: 1000;

    left: 50%;
    bottom: calc(100% + 8px);

    transform:
        translateX(-50%);

    min-width: 190px;

    padding: 8px 10px;

    border-radius: 8px;

    border:
        1px solid
        rgba(128, 128, 128, 0.28);

    background:
        var(--st-secondary-background-color);

    color:
        var(--st-text-color);

    font-size: 0.74rem;

    line-height: 1.35;

    pointer-events: none;

    box-sizing: border-box;
}

.ae-tooltip strong {
    display: block;

    margin-bottom: 2px;
}

.ae-tooltip-secondary {
    opacity: 0.65;
}

.ae-tooltip-action {
    margin-top: 5px;

    opacity: 0.75;

    font-weight: 600;
}

.ae-block-wrapper:hover
.ae-tooltip {
    display: block;
}


/* ==========================================================
   Inspector
   ========================================================== */

.ae-inspector {
    margin-top: 11px;

    padding: 13px 15px;

    border:
        1px solid
        rgba(128, 128, 128, 0.19);

    border-radius: 10px;

    background:
        rgba(128, 128, 128, 0.028);

    box-sizing: border-box;
}

.ae-empty-inspector {
    display: flex;

    flex-direction: column;

    gap: 2px;

    font-size: 0.84rem;
}

.ae-empty-inspector span {
    opacity: 0.62;

    font-size: 0.78rem;
}


/* ==========================================================
   Editor
   ========================================================== */

.ae-editor-header {
    display: flex;

    align-items: flex-start;
    justify-content: space-between;

    gap: 16px;

    margin-bottom: 13px;
}

.ae-editor-title {
    font-size: 0.95rem;
    font-weight: 700;
}

.ae-editor-meta {
    margin-top: 2px;

    font-size: 0.75rem;

    opacity: 0.63;
}

.ae-close {
    width: 32px;
    height: 32px;

    padding: 0;

    border-radius: 7px;

    border:
        1px solid
        rgba(128, 128, 128, 0.24);

    background: transparent;

    color:
        var(--st-text-color);

    font-size: 1.2rem;

    cursor: pointer;
}


/* ==========================================================
   Fields
   ========================================================== */

.ae-editor-grid {
    display: grid;

    grid-template-columns:
        minmax(180px, 1fr)
        minmax(180px, 1fr);

    gap: 12px;
}

.ae-field {
    display: flex;

    flex-direction: column;

    gap: 5px;

    min-width: 0;

    font-size: 0.76rem;
    font-weight: 600;
}

.ae-field select,
.ae-field input {
    width: 100%;

    min-height: 38px;

    padding: 7px 9px;

    box-sizing: border-box;

    border-radius: 7px;

    border:
        1px solid
        rgba(128, 128, 128, 0.35);

    background:
        var(--st-background-color);

    color:
        var(--st-text-color);

    font-family: inherit;

    font-size: 0.88rem;
}


/* ==========================================================
   Number
   ========================================================== */

.ae-number-control {
    display: grid;

    grid-template-columns:
        38px
        minmax(60px, 1fr)
        38px;

    gap: 5px;
}

.ae-number-control button {
    border-radius: 7px;

    border:
        1px solid
        rgba(128, 128, 128, 0.30);

    background:
        var(--st-secondary-background-color);

    color:
        var(--st-text-color);

    font-size: 1.1rem;

    cursor: pointer;
}


/* ==========================================================
   Actions
   ========================================================== */

.ae-actions-row {
    display: flex;

    flex-wrap: wrap;

    gap: 7px;

    margin-top: 12px;
}

.ae-actions-row button,
.ae-split-button {
    min-height: 36px;

    padding: 7px 11px;

    border-radius: 7px;

    border:
        1px solid
        rgba(128, 128, 128, 0.28);

    background:
        var(--st-secondary-background-color);

    color:
        var(--st-text-color);

    font-family: inherit;

    font-size: 0.78rem;

    cursor: pointer;
}

.ae-actions-row button:disabled {
    opacity: 0.35;

    cursor: default;
}

.ae-delete {
    margin-left: auto;
}


/* ==========================================================
   Split
   ========================================================== */

.ae-divider {
    height: 1px;

    margin: 14px 0;

    background:
        rgba(128, 128, 128, 0.18);
}

.ae-split-heading {
    margin-bottom: 10px;
}

.ae-split-heading > div {
    display: flex;

    flex-direction: column;

    gap: 2px;
}

.ae-split-description {
    font-size: 0.74rem;

    opacity: 0.62;
}

.ae-split-controls {
    display: grid;

    grid-template-columns:
        minmax(100px, 1fr)
        auto
        minmax(100px, 1fr)
        auto;

    gap: 8px;

    align-items: end;
}

.ae-split-plus {
    align-self: end;

    padding-bottom: 10px;

    opacity: 0.5;

    font-weight: 700;
}

.ae-split-button {
    height: 38px;

    padding-left: 18px;
    padding-right: 18px;

