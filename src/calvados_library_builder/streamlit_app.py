"""Minimal working Streamlit entry point for the existing builder components."""
from __future__ import annotations

import streamlit as st

from .motifs import get_default_motifs
from .sequences import build_two_motif_design, build_custom_design
from .visualization import render_sequence_design
from .architecture_editor import architecture_editor, blocks_to_design, motif_order_to_blocks


def main() -> None:
    st.set_page_config(page_title="CALVADOS IDP Simulator", layout="wide")
    st.title("CALVADOS · ELP / IDP Library Builder")
    st.caption("Design and inspect motif architectures. Simulation preparation is available through the Python package.")
    motifs = get_default_motifs()
    names = list(motifs)
    left, right = st.columns([1, 2])
    with left:
        motif_a = st.selectbox("Motif A", names, index=0)
        remaining = [x for x in names if x != motif_a]
        motif_b = st.selectbox("Motif B", remaining, index=0)
        count_a = st.number_input("Count A", min_value=0, max_value=10000, value=42)
        count_b = st.number_input("Count B", min_value=0, max_value=10000, value=42)
        architecture = st.selectbox("Pattern", ["Even distribution", "Alternating", "Diblock", "Triblock A-B-A", "Triblock B-A-B", "Block pattern"])
        block_size = st.number_input("Block size (for block pattern)", min_value=1, value=3)
    if count_a + count_b == 0:
        st.info("Select at least one motif.")
        return
    design = build_two_motif_design(motif_a, count_a, motif_b, count_b, architecture, motifs, block_size_a=block_size)
    with right:
        st.subheader("Architecture")
        updated = architecture_editor(motif_order_to_blocks(design.motif_order), motifs, key="main_editor")
        edited = blocks_to_design(updated, motifs)
        render_sequence_design(edited, motifs, compact=True)
        with st.expander("Detailed motif view"):
            render_sequence_design(edited, motifs, compact=False, max_blocks=100)
        st.code(edited.sequence, language="text")
        st.download_button("Export FASTA", f">custom_elp\n{edited.sequence}\n", file_name="custom_elp.fasta", mime="text/plain")


if __name__ == "__main__":
    main()
