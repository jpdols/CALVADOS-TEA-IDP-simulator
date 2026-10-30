"""Local Streamlit interface for motif design and CALVADOS run preparation."""
from __future__ import annotations
import streamlit as st
from .motifs import get_default_motifs
from .sequences import build_two_motif_design
from .visualization import render_sequence_design
from .architecture_editor import architecture_editor, blocks_to_design, motif_order_to_blocks
from .config import SimulationConfig
from .prepare import prepare_simulation
from .diagnostics import available_platforms

def main() -> None:
    st.set_page_config(page_title="CALVADOS IDP Simulator", layout="wide")
    st.title("CALVADOS · ELP / IDP Library Builder")
    st.caption("Local architecture designer and CALVADOS input generator.")
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
        block_size = st.number_input("Block size", min_value=1, value=3)
    if count_a + count_b == 0:
        st.info("Select at least one motif.")
        return
    design = build_two_motif_design(motif_a, count_a, motif_b, count_b, architecture, motifs, block_size_a=block_size)
    with right:
        st.subheader("Sequence architecture")
        updated = architecture_editor(motif_order_to_blocks(design.motif_order), motifs, key="main_editor")
        edited = blocks_to_design(updated, motifs)
        render_sequence_design(edited, motifs, compact=True)
        with st.expander("Detailed motif view"):
            render_sequence_design(edited, motifs, compact=False, max_blocks=100)
        st.code(edited.sequence, language="text")
        st.download_button("Export FASTA", f">custom_elp\n{edited.sequence}\n", file_name="custom_elp.fasta", mime="text/plain")
    st.divider()
    st.subheader("Local simulation setup")
    platforms = available_platforms()
    st.caption("Installed OpenMM platforms: " + ", ".join(platforms))
    name = st.text_input("Simulation name", "custom_elp")
    platform = st.selectbox("CALVADOS platform", ["CPU", "CUDA"], index=0)
    if platform not in platforms:
        st.warning(f"{platform} was not found among installed OpenMM platforms. Check your installation before running.")
    temp = st.number_input("Temperature (K)", min_value=1.0, value=370.0)
    frames = st.number_input("Saved frames", min_value=1, value=50000)
    save_every = st.number_input("Save every N steps", min_value=1, value=1000)
    seed = st.number_input("Random seed", min_value=0, value=1)
    st.caption("Preparation requires a matching residue parameter CSV in data/. This currently prepares input files only; run control UI is still under development.")
    if st.button("Prepare simulation files"):
        try:
            config = SimulationConfig(name=name, sequence=edited.sequence, platform=platform, temperature=temp, n_frames=int(frames), save_every=int(save_every), seed=int(seed))
            run_dir = prepare_simulation(config)
            st.success(f"Prepared {run_dir}")
            st.code(f'cd "{run_dir}"\npython run.py', language="bash")
        except Exception as exc:
            st.error(f"Preparation failed: {exc}")

if __name__ == "__main__":
    main()
