#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from html import escape

import streamlit as st

from .motifs import Motif
from .sequences import SequenceDesign


# ============================================================
# Color helpers
# ============================================================

def hex_to_rgb(
    color: str,
) -> tuple[int, int, int]:
    """
    Convert a HEX color to RGB.
    """

    color = color.lstrip("#")

    return (
        int(color[0:2], 16),
        int(color[2:4], 16),
        int(color[4:6], 16),
    )


def get_contrast_text_color(
    background_color: str,
) -> str:
    """
    Return black or white text depending on background
    brightness.
    """

    r, g, b = hex_to_rgb(
        background_color
    )

    brightness = (
        0.299 * r
        + 0.587 * g
        + 0.114 * b
    )

    if brightness > 165:
        return "#111111"

    return "#FFFFFF"


# ============================================================
# Motif order collapsing
# ============================================================

def collapse_motif_order(
    motif_order: list[str],
) -> list[tuple[str, int]]:
    """
    Collapse consecutive identical motifs into blocks.

    Example
    -------
    [
        "VPGVG",
        "VPGVG",
        "VPGVG",
        "IPAVG",
        "IPAVG",
        "VPGVG",
    ]

    becomes

    [
        ("VPGVG", 3),
        ("IPAVG", 2),
        ("VPGVG", 1),
    ]
    """

    if not motif_order:
        return []

    collapsed: list[tuple[str, int]] = []

    current_motif = motif_order[0]
    current_count = 1

    for motif_name in motif_order[1:]:

        if motif_name == current_motif:

            current_count += 1

        else:

            collapsed.append(
                (
                    current_motif,
                    current_count,
                )
            )

            current_motif = (
                motif_name
            )

            current_count = 1

    collapsed.append(
        (
            current_motif,
            current_count,
        )
    )

    return collapsed


# ============================================================
# Legend
# ============================================================

def build_motif_legend_html(
    motif_names: list[str],
    motifs: dict[str, Motif],
) -> str:
    """
    Build legend for motifs present in the design.
    """

    unique_names = list(
        dict.fromkeys(
            motif_names
        )
    )

    items = []

    for motif_name in unique_names:

        if motif_name not in motifs:
            continue

        motif = motifs[
            motif_name
        ]

        label = escape(
            motif.display_label
        )

        sequence = escape(
            motif.sequence
        )

        color = motif.color

        items.append(
            f"""
            <div class="motif-legend-item">
                <span
                    class="motif-legend-swatch"
                    style="background:{color};"
                ></span>

                <span class="motif-legend-label">
                    <strong>{label}</strong>

                    <span class="motif-legend-sequence">
                        {sequence}
                    </span>
                </span>
            </div>
            """
        )

    return "".join(
        items
    )


# ============================================================
# Compact block-ball rendering
# ============================================================

def build_compact_blocks_html(
    design: SequenceDesign,
    motifs: dict[str, Motif],
    max_blocks: int | None = None,
) -> str:
    """
    Render sequence architecture as collapsed colored balls.

    Consecutive identical motifs become one ball with a
    small count badge.

    Example:
        VPGVG VPGVG VPGVG IPAVG IPAVG

    becomes visually:
        blue(3) yellow(2)
    """

    collapsed_blocks = (
        collapse_motif_order(
            design.motif_order
        )
    )

    truncated = False

    if (
        max_blocks is not None
        and len(
            collapsed_blocks
        ) > max_blocks
    ):

        collapsed_blocks = (
            collapsed_blocks[
                :max_blocks
            ]
        )

        truncated = True

    blocks = []

    for index, (
        motif_name,
        count,
    ) in enumerate(
        collapsed_blocks,
        start=1,
    ):

        if motif_name not in motifs:
            continue

        motif = motifs[
            motif_name
        ]

        color = motif.color

        label = escape(
            motif.display_label
        )

        sequence = escape(
            motif.sequence
        )

        title = escape(
            f"Block {index}: "
            f"{motif.display_label} × {count} "
            f"({motif.sequence})"
        )

        count_html = ""

        if count > 1:

            count_html = (
                f"""
                <span
                    class="motif-ball-count"
                    title="{count} consecutive motifs"
                >
                    {count}
                </span>
                """
            )

        blocks.append(
            f"""
            <div
                class="motif-ball-wrapper"
                title="{title}"
            >

                <div
                    class="motif-ball"
                    style="
                        background:{color};
                    "
                ></div>

                {count_html}

                <span class="motif-ball-hidden-label">
                    {label}
                    {sequence}
                    count {count}
                </span>

            </div>
            """
        )

    if truncated:

        remaining = (
            len(
                collapse_motif_order(
                    design.motif_order
                )
            )
            - len(
                collapsed_blocks
            )
        )

        blocks.append(
            f"""
            <div class="motif-truncated">
                +{remaining} blocks
            </div>
            """
        )

    return "".join(
        blocks
    )


# ============================================================
# Detailed motif rendering
# ============================================================

def build_detailed_blocks_html(
    design: SequenceDesign,
    motifs: dict[str, Motif],
    show_labels: bool = True,
    max_blocks: int | None = None,
) -> str:
    """
    Render each motif individually as a labeled rectangular
    card.
    """

    motif_order = (
        design.motif_order
    )

    truncated = False

    if (
        max_blocks is not None
        and len(
            motif_order
        ) > max_blocks
    ):

        motif_order = (
            motif_order[
                :max_blocks
            ]
        )

        truncated = True

    blocks = []

    for index, motif_name in enumerate(
        motif_order,
        start=1,
    ):

        if motif_name not in motifs:
            continue

        motif = motifs[
            motif_name
        ]

        color = motif.color

        text_color = (
            get_contrast_text_color(
                color
            )
        )

        label = escape(
            motif.display_label
        )

        sequence = escape(
            motif.sequence
        )

        title = escape(
            f"{index}: "
            f"{motif.display_label} "
            f"({motif.sequence})"
        )

        if show_labels:

            content = label

        else:

            content = "&nbsp;"

        sequence_html = ""

        if show_labels:

            sequence_html = (
                f"""
                <span class="motif-block-sequence">
                    {sequence}
                </span>
                """
            )

        blocks.append(
            f"""
            <div
                class="motif-block"
                style="
                    background:{color};
                    color:{text_color};
                "
                title="{title}"
            >

                <span class="motif-block-label">
                    {content}
                </span>

                {sequence_html}

            </div>
            """
        )

    if truncated:

        remaining = (
            design.total_motifs
            - len(
                motif_order
            )
        )

        blocks.append(
            f"""
            <div class="motif-truncated">
                +{remaining} motifs
            </div>
            """
        )

    return "".join(
        blocks
    )


# ============================================================
# Build full design HTML
# ============================================================

def build_design_html(
    design: SequenceDesign,
    motifs: dict[str, Motif],
    show_labels: bool = True,
    compact: bool = False,
    show_legend: bool = True,
    max_blocks: int | None = None,
) -> str:
    """
    Build the complete sequence visualization.

    Compact mode:
        consecutive motifs are collapsed into counted balls.

    Detailed mode:
        each motif gets its own labeled rectangular card.
    """

    legend_html = ""

    if show_legend:

        legend_html = (
            f"""
            <div class="motif-legend">
                {
                    build_motif_legend_html(
                        motif_names=design.motif_order,
                        motifs=motifs,
                    )
                }
            </div>
            """
        )


    # --------------------------------------------------------
    # Compact architecture view
    # --------------------------------------------------------

    if compact:

        blocks_html = (
            build_compact_blocks_html(
                design=design,
                motifs=motifs,
                max_blocks=max_blocks,
            )
        )

        container_class = (
            "motif-ball-container"
        )

        collapsed_count = len(
            collapse_motif_order(
                design.motif_order
            )
        )

        block_summary = (
            f"""
            <span>
                <strong>{collapsed_count}</strong>
                contiguous blocks
            </span>
            """
        )


    # --------------------------------------------------------
    # Detailed motif view
    # --------------------------------------------------------

    else:

        blocks_html = (
            build_detailed_blocks_html(
                design=design,
                motifs=motifs,
                show_labels=show_labels,
                max_blocks=max_blocks,
            )
        )

        container_class = (
            "motif-block-container"
        )

        block_summary = ""


    # ========================================================
    # HTML + CSS
    # ========================================================

    return f"""
    <style>

        /* ==================================================
           Main visualizer
           ================================================== */

        .sequence-visualizer {{
            width: 100%;
            box-sizing: border-box;
        }}


        /* ==================================================
           Legend
           ================================================== */

        .motif-legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px 18px;
            margin-bottom: 14px;
        }}

        .motif-legend-item {{
            display: flex;
            align-items: center;
            gap: 7px;
            font-size: 0.9rem;
        }}

        .motif-legend-swatch {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            border: 1px solid rgba(0, 0, 0, 0.15);
            display: inline-block;
            box-sizing: border-box;
        }}

        .motif-legend-label {{
            display: flex;
            gap: 5px;
            align-items: baseline;
        }}

        .motif-legend-sequence {{
            opacity: 0.62;
            font-size: 0.78rem;
        }}


        /* ==================================================
           Compact architecture container
           ================================================== */

        .motif-ball-container {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;

            gap: 12px;

            width: 100%;

            padding:
                16px 14px;

            border:
                1px solid
                rgba(128, 128, 128, 0.18);

            border-radius:
                10px;

            box-sizing:
                border-box;

            background:
                rgba(128, 128, 128, 0.035);
        }}


        /* ==================================================
           Compact motif ball
           ================================================== */

        .motif-ball-wrapper {{
            position: relative;

            width: 31px;
            height: 31px;

            flex:
                0 0 31px;

            display:
                inline-flex;

            align-items:
                center;

            justify-content:
                center;

            overflow:
                visible;

            cursor:
                default;
        }}

        .motif-ball {{
            width: 27px;
            height: 27px;

            border-radius:
                50%;

            border:
                1px solid
                rgba(0, 0, 0, 0.18);

            box-sizing:
                border-box;

            transition:
                transform 0.12s ease,
                border-color 0.12s ease;
        }}

        .motif-ball-wrapper:hover
        .motif-ball {{
            transform:
                scale(1.08);

            border-color:
                rgba(0, 0, 0, 0.38);
        }}


        /* ==================================================
           Count badge

           Example:
               blue ball with small "4"
               in lower-right corner
           ================================================== */

        .motif-ball-count {{
            position:
                absolute;

            right:
                -5px;

            bottom:
                -4px;

            min-width:
                15px;

            height:
                15px;

            padding:
                0 3px;

            border-radius:
                8px;

            display:
                flex;

            align-items:
                center;

            justify-content:
                center;

            box-sizing:
                border-box;

            background:
                #FFFFFF;

            color:
                #171717;

            border:
                1px solid
                rgba(0, 0, 0, 0.20);

            font-size:
                9px;

            font-weight:
                750;

            line-height:
                1;
        }}


        /* Screen-reader / semantic helper */
        .motif-ball-hidden-label {{
            position:
                absolute;

            width:
                1px;

            height:
                1px;

            padding:
                0;

            margin:
                -1px;

            overflow:
                hidden;

            clip:
                rect(0, 0, 0, 0);

            white-space:
                nowrap;

            border:
                0;
        }}


        /* ==================================================
           Detailed motif cards
           ================================================== */

        .motif-block-container {{
            display:
                flex;

            flex-wrap:
                wrap;

            align-items:
                stretch;

            gap:
                4px;

            width:
                100%;

            padding:
                10px;

            border:
                1px solid
                rgba(128, 128, 128, 0.18);

            border-radius:
                9px;

            box-sizing:
                border-box;

            background:
                rgba(128, 128, 128, 0.035);
        }}

        .motif-block {{
            min-width:
                62px;

            padding:
                7px 9px;

            border-radius:
                6px;

            border:
                1px solid
                rgba(0, 0, 0, 0.12);

            box-sizing:
                border-box;

            display:
                flex;

            flex-direction:
                column;

            justify-content:
                center;

            align-items:
                center;

            line-height:
                1.05;

            cursor:
                default;
        }}

        .motif-block-label {{
            font-size:
                0.78rem;

            font-weight:
                650;

            white-space:
                nowrap;
        }}

        .motif-block-sequence {{
            margin-top:
                3px;

            font-size:
                0.62rem;

            opacity:
                0.75;

            white-space:
                nowrap;
        }}


        /* ==================================================
           Truncation
           ================================================== */

        .motif-truncated {{
            min-height:
                24px;

            padding:
                6px 10px;

            display:
                flex;

            align-items:
                center;

            justify-content:
                center;

            border-radius:
                8px;

            border:
                1px dashed
                rgba(128, 128, 128, 0.5);

            font-size:
                0.75rem;

            opacity:
                0.75;
        }}


        /* ==================================================
           Summary
           ================================================== */

        .sequence-summary {{
            display:
                flex;

            flex-wrap:
                wrap;

            gap:
                8px 20px;

            margin-top:
                10px;

            font-size:
                0.82rem;

            opacity:
                0.75;
        }}

    </style>


    <div class="sequence-visualizer">

        {legend_html}

        <div class="{container_class}">
            {blocks_html}
        </div>

        <div class="sequence-summary">

            <span>
                <strong>{design.total_motifs}</strong>
                motifs
            </span>

            <span>
                <strong>{design.total_aa}</strong>
                amino acids
            </span>

            <span>
                <strong>{len(design.motif_counts)}</strong>
                motif types
            </span>

            {block_summary}

        </div>

    </div>
    """


# ============================================================
# Streamlit renderer

def render_sequence_design(
    design: SequenceDesign,
    motifs: dict[str, Motif],
    show_labels: bool = True,
    compact: bool = False,
    show_legend: bool = True,
    max_blocks: int | None = None,
) -> None:
    """Render a motif architecture in the Streamlit page.

    Uses st.html rather than st.markdown so the CSS/HTML visualizer is
    displayed as markup, not escaped text.
    """
    html = build_design_html(
        design=design,
        motifs=motifs,
        show_labels=show_labels,
        compact=compact,
        show_legend=show_legend,
        max_blocks=max_blocks,
    )
    st.html(html)
