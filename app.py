#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from calvados_library_builder.architecture_editor import (
    architecture_editor,
    blocks_to_design,
    get_block_statistics,
    sanitize_blocks,
)
from calvados_library_builder.batch import (
    add_simulation,
    advance_batch,
    create_batch,
    estimate_batch_remaining_seconds,
    get_batch_counts,
    get_batch_progress,
    get_current_summary,
    load_batch,
    remove_simulation,
    start_batch,
)
from calvados_library_builder.config import (
    DEFAULT_BOX_SIZE,
    DEFAULT_IONIC_STRENGTH,
    DEFAULT_N_FRAMES,
    DEFAULT_PH,
    DEFAULT_PLATFORM,
    DEFAULT_SAVE_EVERY,
    DEFAULT_TEMPERATURE,
    RUNS_DIR,
    SimulationConfig,
)
from calvados_library_builder.motifs import (
    Motif,
    add_motif,
    create_motif,
    get_default_motifs,
)
from calvados_library_builder.prepare import prepare_simulation
from calvados_library_builder.runner import format_duration, stop_run
from calvados_library_builder.diagnostics import available_platforms
from calvados_library_builder.visualization import render_sequence_design


# ============================================================
# Page
# ============================================================

st.set_page_config(
    page_title="CALVADOS Library Builder",
    page_icon="🧬",
    layout="wide",
)

st.title("CALVADOS Library Builder")

st.caption(
    "Build ELP-like sequences from motif building blocks, "
    "edit their architecture interactively and run CALVADOS locally."
)


# ============================================================
# Session state
# ============================================================

if "motifs" not in st.session_state:
    st.session_state["motifs"] = get_default_motifs()

if "architecture_blocks" not in st.session_state:
    st.session_state["architecture_blocks"] = []

if "architecture_revision" not in st.session_state:
    st.session_state["architecture_revision"] = 0

if "active_batch_dir" not in st.session_state:
    st.session_state["active_batch_dir"] = None

if "last_added_name" not in st.session_state:
    st.session_state["last_added_name"] = None

motifs: dict[str, Motif] = st.session_state["motifs"]


# ============================================================
# General helpers
# ============================================================

def clean_aa_sequence(sequence: str) -> str:
    return (
        sequence
        .replace(" ", "")
        .replace("\n", "")
        .replace("\r", "")
        .replace("\t", "")
        .upper()
    )


def sanitize_folder_name(name: str) -> str:
    name = name.strip()

    name = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        name,
    )

    name = re.sub(
        r"\s+",
        "_",
        name,
    )

    name = re.sub(
        r"_+",
        "_",
        name,
    )

    return name.strip("._ ")


def get_batch_directory(batch_name: str) -> Path:
    safe_name = sanitize_folder_name(batch_name)

    if not safe_name:
        raise ValueError(
            "Run name cannot be empty."
        )

    return (
        RUNS_DIR
        / safe_name
    ).resolve()


def get_active_batch():
    batch_dir = st.session_state.get(
        "active_batch_dir"
    )

    if not batch_dir:
        return None

    batch_dir = Path(batch_dir)

    state_file = (
        batch_dir
        / "batch_state.json"
    )

    if not state_file.exists():
        return None

    try:
        return load_batch(
            batch_dir
        )

    except Exception:
        return None


def get_or_create_batch(
    batch_name: str,
):
    batch_dir = get_batch_directory(
        batch_name
    )

    state_path = (
        batch_dir
        / "batch_state.json"
    )

    if state_path.exists():
        batch = load_batch(
            batch_dir
        )

    else:
        batch = create_batch(
            name=batch_name.strip(),
            batch_dir=batch_dir,
        )

    st.session_state[
        "active_batch_dir"
    ] = str(batch_dir)

    return batch


# ============================================================
# Architecture helpers
# ============================================================

def refresh_architecture_component() -> None:
    """
    Force the frontend architecture component to be recreated.

    This is useful when blocks are changed externally,
    for example through Add or Clear.
    """

    st.session_state[
        "architecture_revision"
    ] += 1


def get_current_blocks() -> list[dict]:
    return sanitize_blocks(
        blocks=st.session_state[
            "architecture_blocks"
        ],
        motifs=st.session_state[
            "motifs"
        ],
    )


def set_current_blocks(
    blocks: list[dict],
    *,
    refresh_editor: bool = False,
) -> None:
    st.session_state[
        "architecture_blocks"
    ] = sanitize_blocks(
        blocks=blocks,
        motifs=st.session_state[
            "motifs"
        ],
    )

    if refresh_editor:
        refresh_architecture_component()


def add_building_block(
    motif_name: str,
    count: int,
) -> None:
    """
    Add a motif building block to the end of the architecture.

    If the final block already contains the same motif,
    increase its count instead of making another adjacent block.
    """

    count = max(
        1,
        int(count),
    )

    blocks = get_current_blocks()

    if (
        blocks
        and blocks[-1]["motif"] == motif_name
    ):
        blocks[-1]["count"] += count

    else:
        blocks.append(
            {
                "motif": motif_name,
                "count": count,
            }
        )

    set_current_blocks(
        blocks,
        refresh_editor=True,
    )


def clear_architecture() -> None:
    st.session_state[
        "architecture_blocks"
    ] = []

    refresh_architecture_component()


def reset_motif_library() -> None:
    st.session_state[
        "motifs"
    ] = get_default_motifs()

    # Remove blocks referring to custom motifs that
    # no longer exist after the reset.
    st.session_state[
        "architecture_blocks"
    ] = sanitize_blocks(
        blocks=st.session_state[
            "architecture_blocks"
        ],
        motifs=st.session_state[
            "motifs"
        ],
    )

    refresh_architecture_component()


# ============================================================
# 1. Sequence design
# ============================================================

st.header(
    "1. Sequence design"
)

name_col, mode_col = st.columns(
    [2, 1]
)

with name_col:
    sequence_name = st.text_input(
        "Sequence / simulation name",
        value="test_sequence",
    )

with mode_col:
    input_mode = st.selectbox(
        "Input mode",
        [
            "Motif builder",
            "Custom amino-acid sequence",
        ],
    )

clean_sequence = ""
current_design = None


# ============================================================
# LEGO motif builder
# ============================================================

if input_mode == "Motif builder":

    motifs = st.session_state[
        "motifs"
    ]

    # ========================================================
    # Building block library
    # ========================================================

    st.subheader(
        "Building blocks"
    )

    st.caption(
        "Choose how many copies of a motif you want and press Add. "
        "If the final architecture block is already the same motif, "
        "the new copies are added to that block."
    )

    motif_items = list(
        motifs.items()
    )

    columns_per_row = 3

    for row_start in range(
        0,
        len(motif_items),
        columns_per_row,
    ):

        row_items = motif_items[
            row_start:
            row_start + columns_per_row
        ]

        row_columns = st.columns(
            columns_per_row
        )

        for column, (
            motif_name,
            motif,
        ) in zip(
            row_columns,
            row_items,
        ):

            with column:

                st.html(
                    f"""
<div style="
    border: 1px solid rgba(128,128,128,0.22);
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 7px;
">
    <div style="
        display: flex;
        align-items: center;
        gap: 9px;
        margin-bottom: 3px;
    ">
        <span style="
            display: inline-block;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: {motif.color};
            border: 1px solid rgba(0,0,0,0.18);
            flex-shrink: 0;
        ">
        </span>

        <strong>
            {motif.display_label}
        </strong>
    </div>

    <div style="
        opacity: 0.62;
        font-size: 0.78rem;
        margin-left: 31px;
    ">
        {motif.sequence} · {motif.length} aa
    </div>
</div>
"""
                )

                count_key = (
                    f"builder_count_{motif_name}"
                )

                add_key = (
                    f"builder_add_{motif_name}"
                )

                motif_add_count = st.number_input(
                    "Count",
                    min_value=1,
                    value=1,
                    step=1,
                    key=count_key,
                )

                if st.button(
                    f"Add {motif.display_label}",
                    key=add_key,
                    use_container_width=True,
                ):

                    add_building_block(
                        motif_name=motif_name,
                        count=int(
                            motif_add_count
                        ),
                    )

                    st.rerun()


    # ========================================================
    # Custom motif management
    # ========================================================

    with st.expander(
        "Add or manage motifs"
    ):

        st.caption(
            "Custom motifs immediately become available as "
            "additional LEGO building blocks."
        )

        custom_col1, custom_col2, custom_col3 = (
            st.columns(
                [1, 1, 0.55]
            )
        )

        with custom_col1:
            custom_motif_name = st.text_input(
                "Motif name",
                placeholder="VPGFG",
                key="custom_motif_name",
            )

        with custom_col2:
            custom_motif_sequence = st.text_input(
                "Motif sequence",
                placeholder="VPGFG",
                key="custom_motif_sequence",
            )

        with custom_col3:
            custom_motif_color = st.color_picker(
                "Color",
                "#7F7F7F",
                key="custom_motif_color",
            )

        custom_button_col1, custom_button_col2 = (
            st.columns(2)
        )

        with custom_button_col1:

            if st.button(
                "Add custom motif",
                use_container_width=True,
            ):

                try:
                    new_motif = create_motif(
                        name=custom_motif_name,
                        sequence=custom_motif_sequence,
                        color=custom_motif_color,
                    )

                    st.session_state[
                        "motifs"
                    ] = add_motif(
                        motifs=motifs,
                        motif=new_motif,
                    )

                    refresh_architecture_component()

                    st.rerun()

                except Exception as error:
                    st.error(
                        str(error)
                    )

        with custom_button_col2:

            if st.button(
                "Reset motif library",
                use_container_width=True,
            ):

                reset_motif_library()

                st.rerun()


    # ========================================================
    # Architecture
    # ========================================================

    st.subheader(
        "Architecture"
    )

    architecture_action_col1, architecture_action_col2 = (
        st.columns(
            [4, 1]
        )
    )

    with architecture_action_col1:

        st.caption(
            "Click = edit · double-click = split · drag = reorder. "
            "Identical neighbouring blocks merge after structural edits."
        )

    with architecture_action_col2:

        if st.button(
            "Clear architecture",
            use_container_width=True,
            disabled=(
                len(
                    get_current_blocks()
                )
                == 0
            ),
        ):

            clear_architecture()

            st.rerun()


    starting_blocks = get_current_blocks()

    if starting_blocks:

        editor_key = (
            "architecture_editor_"
            f"{st.session_state['architecture_revision']}"
        )

        edited_blocks = architecture_editor(
            blocks=starting_blocks,
            motifs=motifs,
            key=editor_key,
        )

        # Editor output is the canonical architecture.
        st.session_state[
            "architecture_blocks"
        ] = edited_blocks

        try:
            current_design = blocks_to_design(
                blocks=edited_blocks,
                motifs=motifs,
            )

            clean_sequence = (
                current_design.sequence
            )

        except Exception as error:

            st.error(
                "Could not construct sequence from "
                f"architecture: {error}"
            )

            current_design = None

    else:

        st.info(
            "Architecture is empty. "
            "Add a building block above to begin."
        )


    # ========================================================
    # Current design statistics
    # ========================================================

    if current_design is not None:

        statistics = get_block_statistics(
            blocks=st.session_state[
                "architecture_blocks"
            ],
            motifs=motifs,
        )

        st.markdown(
            "#### Current design"
        )

        metric_col1, metric_col2, metric_col3, metric_col4 = (
            st.columns(4)
        )

        with metric_col1:
            st.metric(
                "Blocks",
                statistics[
                    "blocks"
                ],
            )

        with metric_col2:
            st.metric(
                "Motifs",
                statistics[
                    "total_motifs"
                ],
            )

        with metric_col3:
            st.metric(
                "Sequence length",
                f"{statistics['total_aa']} aa",
            )

        with metric_col4:
            st.metric(
                "Motif types",
                len(
                    statistics[
                        "motif_counts"
                    ]
                ),
            )


        # ====================================================
        # Composition
        # ====================================================

        with st.expander(
            "Composition",
            expanded=True,
        ):

            motif_counts = statistics[
                "motif_counts"
            ]

            total_motifs = max(
                1,
                statistics[
                    "total_motifs"
                ],
            )

            for motif_name, count in (
                motif_counts.items()
            ):

                motif = motifs[
                    motif_name
                ]

                percentage = (
                    count
                    / total_motifs
                    * 100.0
                )

                comp_col1, comp_col2, comp_col3 = (
                    st.columns(
                        [2.5, 1, 1]
                    )
                )

                with comp_col1:

                    st.html(
                        f"""
<div style="
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 32px;
">
    <span style="
        width: 15px;
        height: 15px;
        border-radius: 50%;
        background: {motif.color};
        display: inline-block;
        border: 1px solid rgba(0,0,0,0.15);
        flex-shrink: 0;
    ">
    </span>

    <strong>
        {motif.display_label}
    </strong>

    <span style="
        opacity: 0.55;
        font-size: 0.78rem;
    ">
        {motif.sequence}
    </span>
</div>
"""
                    )

                with comp_col2:
                    st.write(
                        f"**{count}** motifs"
                    )

                with comp_col3:
                    st.write(
                        f"**{percentage:.1f}%**"
                    )


        # ====================================================
        # Final sequence inspection
        # ====================================================

        with st.expander(
            "Inspect final sequence",
            expanded=False,
        ):

            view_mode = st.radio(
                "View",
                [
                    "Compact",
                    "Detailed",
                ],
                horizontal=True,
                key="final_sequence_view",
            )

            render_sequence_design(
                design=current_design,
                motifs=motifs,
                compact=(
                    view_mode
                    == "Compact"
                ),
                show_labels=(
                    view_mode
                    == "Detailed"
                ),
                show_legend=True,
            )

            st.markdown(
                "##### Exact motif order"
            )

            st.text_area(
                "Exact motif order",
                " | ".join(
                    current_design.motif_order
                ),
                height=130,
                disabled=True,
                label_visibility="collapsed",
            )

            st.markdown(
                "##### Amino-acid sequence"
            )

            st.text_area(
                "Final amino-acid sequence",
                clean_sequence,
                height=180,
                disabled=True,
                label_visibility="collapsed",
            )


# ============================================================
# Custom AA sequence
# ============================================================

else:

    sequence_input = st.text_area(
        "Amino-acid sequence",
        height=220,
        placeholder=(
            "Paste a one-letter amino-acid sequence..."
        ),
    )

    clean_sequence = clean_aa_sequence(
        sequence_input
    )

    if clean_sequence:

        custom_seq_col1, custom_seq_col2 = (
            st.columns(2)
        )

        with custom_seq_col1:

            st.metric(
                "Sequence length",
                f"{len(clean_sequence)} aa",
            )

        with custom_seq_col2:

            st.metric(
                "Unique residue types",
                len(
                    set(
                        clean_sequence
                    )
                ),
            )


# ============================================================
# Final design status
# ============================================================

if clean_sequence:

    st.download_button("Download FASTA", f">{sanitize_folder_name(sequence_name) or 'sequence'}\n{clean_sequence}\n", file_name=f"{sanitize_folder_name(sequence_name) or 'sequence'}.fasta", mime="text/plain")

    st.success(
        f"Final sequence ready: "
        f"{len(clean_sequence)} aa"
    )

else:

    st.info(
        "Build or enter a sequence before preparing a simulation."
    )


# ============================================================
# 2. Simulation settings
# ============================================================

st.header(
    "2. Simulation settings"
)

settings_col1, settings_col2, settings_col3 = (
    st.columns(3)
)

with settings_col1:

    temperature = st.number_input(
        "Temperature (K)",
        min_value=1.0,
        value=float(
            DEFAULT_TEMPERATURE
        ),
        step=10.0,
    )

    pH = st.number_input(
        "pH",
        min_value=0.0,
        max_value=14.0,
        value=float(
            DEFAULT_PH
        ),
        step=0.1,
    )

with settings_col2:

    ionic_strength = st.number_input(
        "Ionic strength (M)",
        min_value=0.0,
        value=float(
            DEFAULT_IONIC_STRENGTH
        ),
        step=0.01,
    )

    box_size = st.number_input(
        "Box size (nm)",
        min_value=1.0,
        value=float(
            DEFAULT_BOX_SIZE
        ),
        step=1.0,
    )

with settings_col3:

    platform_options = ["CPU", "CUDA"]

    platform_index = (
        platform_options.index(
            DEFAULT_PLATFORM
        )
        if DEFAULT_PLATFORM
        in platform_options
        else 0
    )

    platform = st.selectbox(
        "Platform",
        platform_options,
        index=platform_index,
    )

    detected_platforms = available_platforms()
    st.caption("OpenMM platforms detected: " + ", ".join(detected_platforms))
    if platform not in detected_platforms:
        st.warning(f"{platform} platform is not available in this OpenMM installation.")


# ============================================================
# Simulation length
# ============================================================

st.subheader(
    "Simulation length"
)

length_col1, length_col2, length_col3 = (
    st.columns(3)
)

with length_col1:

    n_frames = st.number_input(
        "Number of frames",
        min_value=1,
        value=int(