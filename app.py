"""CALVADOS ELP Studio — design, simulate and analyze without a long configuration form.

Advanced original UI: streamlit run legacy_app.py
"""
from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
import streamlit as st

from calvados_library_builder.analysis import (
    THETA_REF_NM, analyze_run, locate_files, theta_rg,
)
from calvados_library_builder.batch import (
    add_simulation, advance_batch, create_batch, get_batch_counts,
    load_batch, start_batch,
)
from calvados_library_builder.config import RUNS_DIR, SimulationConfig
from calvados_library_builder.designs import Candidate, make_library, simple_elp, validate_sequence
from calvados_library_builder.diagnostics import available_platforms
from calvados_library_builder.preflight import inspect_run
from calvados_library_builder.prepare import prepare_simulation
from calvados_library_builder.runner import get_run_summary, stop_run
from calvados_library_builder.motifs import get_default_motifs, create_motif
from calvados_library_builder.motif_canvas import motif_canvas
from calvados_library_builder.studio_sequence import (
    default_groups, groups_to_sequence, groups_to_architecture,
    count_motifs, normalize_groups, extract_single_fasta,
    segment_raw_sequence, load_custom_motifs, save_custom_motifs,
    load_draft, save_draft,
)


st.set_page_config(page_title="ELP Studio", page_icon="🧬", layout="wide")
st.title("ELP Studio")
st.caption("Design a protein • simulate with CALVADOS • inspect molecular behaviour")

ROOT = RUNS_DIR
ROOT.mkdir(parents=True, exist_ok=True)
platforms = available_platforms()
choices = [p for p in ("CPU", "CUDA") if p in platforms]
if not choices:
    choices = ["CPU"]


def safe_label(value: str) -> str:
    label = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._")
    if not label:
        raise ValueError("Enter a valid name.")
    return label


def batch_paths() -> list[Path]:
    return sorted(ROOT.glob("*/batch_state.json"), reverse=True)


def run_paths() -> list[Path]:
    found = {p.parent for p in ROOT.glob("*/*/config.yaml")}
    found.update(p.parent for p in ROOT.glob("*/config.yaml"))
    return sorted(found, key=lambda p: str(p).lower())


def choose_batch_name(value: str) -> Path:
    return ROOT / safe_label(value)


def load_or_create_batch(name: str):
    directory = choose_batch_name(name)
    return load_batch(directory) if (directory / "batch_state.json").exists() else create_batch(name, directory)


def preview(candidates: list[Candidate]) -> None:
    st.caption(f"{len(candidates)} sequence(s) generated")
    st.dataframe(
        pd.DataFrame([
            {
                "Name": c.name,
                "Architecture": c.architecture,
                "Length (aa)": len(c.sequence),
                "Sequence preview": c.sequence[:60] + ("…" if len(c.sequence) > 60 else ""),
            }
            for c in candidates
        ]), use_container_width=True, hide_index=True,
    )


design_tab, simulate_tab, analyze_tab = st.tabs(
    ["1  Design", "2  Simulate", "3  Analyze"]
)

with design_tab:
    st.subheader("Design your ELP")
    st.caption("Build directly with motif balls. The colored architecture below is the sequence used for simulation.")

    motif_path = ROOT / "_custom_motifs.json"
    if "studio_motifs" not in st.session_state:
        try:
            st.session_state["studio_motifs"] = {
                **get_default_motifs(), **load_custom_motifs(motif_path)
            }
        except (ValueError, OSError, KeyError) as exc:
            st.session_state["studio_motifs"] = get_default_motifs()
            st.error(f"Could not load custom motif library: {exc}")
    motifs = st.session_state["studio_motifs"]
    draft_path = ROOT / "_current_elp_draft.json"
    if "studio_groups" not in st.session_state:
        try:
            draft_name, draft_groups = load_draft(draft_path, motifs)
        except (ValueError, OSError, KeyError) as exc:
            draft_name, draft_groups = "test_sequence", default_groups()
            st.warning(f"Could not restore saved ELP draft: {exc}")
        st.session_state["studio_groups"] = draft_groups
        st.session_state.setdefault("studio_sequence_name", draft_name)
    st.session_state.setdefault("studio_canvas_revision", 0)

    name = st.text_input("Sequence name", key="studio_sequence_name")
    st.caption("Autosaved locally: motif palette and current ELP are restored when you reopen the app.")

    # Custom motif editor stays compact and does not replace existing colors.
    with st.expander("Motif palette · add your own color and amino-acid sequence"):
        st.caption("The standard motifs retain their thesis colors, including purple RGD. New motifs are saved on this computer.")
        colors = st.columns(3)
        for idx, motif in enumerate(motifs.values()):
            with colors[idx % 3]:
                st.markdown(
                    f'<span style="display:inline-block;background:{motif.color};'
                    f'width:13px;height:13px;border-radius:50%;margin-right:8px"></span>'
                    f'<b>{motif.name}</b> · {motif.sequence}', unsafe_allow_html=True
                )
        with st.form("new_motif_form", clear_on_submit=True):
            left, mid, right = st.columns([1, 2, 1])
            with left:
                motif_name = st.text_input("New motif name", placeholder="VPGFG")
            with mid:
                motif_sequence = st.text_input("Amino acids", placeholder="VPGFG")
            with right:
                motif_color = st.color_picker("Color", "#00AEEF")
            if st.form_submit_button("Add motif to palette"):
                try:
                    new_motif = create_motif(motif_name, motif_sequence, motif_color)
                    if new_motif.name in motifs:
                        raise ValueError("Motif already exists. Choose a different name.")
                    custom = {
                        key: value for key, value in motifs.items()
                        if key not in get_default_motifs()
                    }
                    custom[new_motif.name] = new_motif
                    save_custom_motifs(motif_path, custom)
                    st.session_state["studio_motifs"] = {
                        **get_default_motifs(), **custom
                    }
                    st.success(f"Added {new_motif.name} with color {new_motif.color}.")
                    st.rerun()
                except (ValueError, OSError) as exc:
                    st.error(str(exc))

    # The canvas is always visible, directly at the top of the design workflow.
    motif_definitions = {
        n: {"sequence": m.sequence, "color": m.color, "label": m.display_label}
        for n, m in motifs.items()
    }
    canvas = motif_canvas(
        groups=st.session_state["studio_groups"],
        motifs=motif_definitions,
        revision=st.session_state["studio_canvas_revision"],
    )
    try:
        edited_groups = normalize_groups(canvas.groups, motifs)
        st.session_state["studio_groups"] = edited_groups
        # Save only on changes. Browser refreshes and Streamlit reruns
        # then restore the exact last valid sequence and motif count.
        save_key = (name, repr(edited_groups))
        if st.session_state.get("_studio_last_saved") != save_key:
            try:
                save_draft(draft_path, name, edited_groups, motifs)
                st.session_state["_studio_last_saved"] = save_key
            except (OSError, ValueError) as exc:
                st.error(f"Could not save ELP draft: {exc}")
    except (ValueError, TypeError) as exc:
        edited_groups = st.session_state["studio_groups"]
        st.error(f"Invalid architecture: {exc}")

    # Pasted raw sequences can still be imported without losing unmatched residues.
    with st.expander("Paste an amino-acid sequence or FASTA instead"):
        st.caption("Known motifs are converted into colored balls; unmatched residues remain as grey fragments.")
        pasted = st.text_area(
            "Paste sequence (one FASTA record or plain amino acids)",
            key="studio_paste_sequence", height=110,
        )
        if st.button("Replace canvas with pasted sequence"):
            try:
                parsed, extras = segment_raw_sequence(pasted, motifs)
                if extras:
                    custom = {
                        key: value for key, value in motifs.items()
                        if key not in get_default_motifs()
                    }
                    custom.update(extras)
                    save_custom_motifs(motif_path, custom)
                    st.session_state["studio_motifs"] = {
                        **get_default_motifs(), **custom
                    }
                st.session_state["studio_groups"] = parsed
                st.session_state["studio_canvas_revision"] += 1
                st.rerun()
            except (ValueError, OSError) as exc:
                st.error(str(exc))

    candidates: list[Candidate] = []
    try:
        sequence = groups_to_sequence(edited_groups, motifs)
        architecture = groups_to_architecture(edited_groups, motifs)
        if sequence:
            candidates = [Candidate(safe_label(name), sequence, architecture)]
    except ValueError as exc:
        st.warning(str(exc))

    if candidates:
        counts = count_motifs(edited_groups, motifs)
        a, b, c = st.columns(3)
        a.metric("Amino acids", len(sequence))
        b.metric("Motifs", sum(counts.values()))
        c.metric("Blocks", len(edited_groups))
        with st.expander("Exact sequence and composition"):
            st.code(sequence, language="text")
            st.caption(architecture)
            st.dataframe(
                pd.DataFrame([
                    {"Motif": n, "Count": k, "Fraction": k / sum(counts.values())}
                    for n, k in counts.items()
                ]), hide_index=True, use_container_width=True,
            )
        st.download_button(
            "Download sequence FASTA",
            data=f">{safe_label(name)}\n{sequence}\n",
            file_name=f"{safe_label(name)}.fasta", mime="text/plain",
        )
    else:
        st.info("Use the palette above to add a motif and begin your ELP.")

    with st.expander("Optional: build a composition-matched two-motif library"):
        st.caption("Use the same saved motif palette to generate alternating, diblock, central and shuffled designs.")
        p1, p2, p3 = st.columns(3)
        with p1:
            prefix_name = st.text_input("Library name", "VGIP_screen")
            motif_names = list(motifs)
            motif_a = st.selectbox("Motif A", motif_names, key="lib_motif_a")
        with p2:
            motif_b = st.selectbox(
                "Motif B", motif_names, index=min(1, len(motif_names)-1),
                key="lib_motif_b",
            )
        with p3:
            n_motifs = st.number_input("Motifs per design", 2, 2000, 84)
        fractions = st.multiselect(
            "Motif B fractions", [0.0, 0.1, 0.25, 0.31, 0.5, 0.67, 0.75, 0.86, 0.9, 1.0],
            default=[0.1, 0.31, 0.5, 0.67, 0.86],
            format_func=lambda x: f"{x:.0%} B",
        )
        architectures = st.multiselect(
            "Architectures", ["alternating", "diblock", "central", "shuffled"],
            default=["alternating", "diblock", "central", "shuffled"],
        )
        seed = st.number_input("Shuffle seed", 0, 999999, 1)
        if st.button("Generate library"):
            try:
                library = make_library(
                    safe_label(prefix_name),
                    motifs[motif_a].sequence, motifs[motif_b].sequence,
                    int(n_motifs), fractions, architectures, seed=int(seed),
                )
                st.session_state["studio_library"] = library
            except ValueError as exc:
                st.error(str(exc))
        library = st.session_state.get("studio_library", [])
        if library:
            preview(library)
            st.download_button(
                "Download library FASTA",
                data="".join(f">{c.name}\n{c.sequence}\n" for c in library),
                file_name="elp_library.fasta", mime="text/plain",
            )
            use_library = st.checkbox("Prepare this library instead of the single ELP")
            if use_library:
                candidates = library

    st.divider()
    st.subheader("Prepare simulations")
    st.caption("All designs use the same conditions. Existing simulation folders will never be overwritten.")
    batch_name = st.text_input("Experiment name", "first_test")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        temperature = st.selectbox("Temperature (K)", list(range(300, 401, 10)), index=7)
    with s2:
        platform = st.selectbox("Compute", choices)
    with s3:
        frames = st.number_input("Saved frames", 2, 50000, 50)
    with s4:
        save_every = st.number_input("Steps per frame", 1, 1000000, 1000)
    with st.expander("Advanced simulation settings"):
        box_nm = st.number_input("Box length (nm)", 5.0, 500.0, 50.0)
        ph = st.number_input("pH", 0.0, 14.0, 7.0)
        ionic = st.number_input("Ionic strength (M)", 0.0, 5.0, 0.17)
        first_seed = st.number_input("Starting random seed", 0, 2147483646, 1)
    st.caption(
        f"{int(frames) * int(save_every):,} integration steps per sequence; "
        f"{len(candidates)} sequence(s), one single-chain simulation each."
    )
    if st.button("Prepare designs", type="primary", disabled=not candidates):
        try:
            b = load_or_create_batch(batch_name)
            prepared = []
            for i, candidate in enumerate(candidates):
                cfg = SimulationConfig(
                    name=candidate.name, sequence=candidate.sequence,
                    temperature=float(temperature), pH=float(ph),
                    ionic_strength=float(ionic), box_size=float(box_nm),
                    n_frames=int(frames), save_every=int(save_every),
                    platform=platform, seed=int(first_seed) + i,
                )
                run = prepare_simulation(cfg, batch_dir=Path(b.batch_dir))
                b = add_simulation(b, candidate.name, run, int(frames))
                prepared.append(candidate.name)
            st.success(f"Prepared {len(prepared)} run(s) in '{b.name}'. Open Simulate to start.")
        except Exception as exc:
            st.error(f"Preparation stopped: {exc}")
            st.caption("Previously prepared sequences are retained; inspect the batch before retrying.")

with simulate_tab:
    st.subheader("Your simulation queues")
    batches = batch_paths()
    if not batches:
        st.info("No experiments yet. Create sequences in Design.")
    else:
        chosen = st.selectbox("Experiment", batches, format_func=lambda p: p.parent.name)
        bdir = chosen.parent
        batch = load_batch(bdir)
        if batch.status == "running":
            try:
                batch = advance_batch(batch)
            except Exception as exc:
                st.error(f"Queue monitor error: {exc}")
        counts = get_batch_counts(batch)
        a, bb, c, d = st.columns(4)
        a.metric("Queued", counts["queued"])
        bb.metric("Running", counts["running"])
        c.metric("Finished", counts["finished"])
        d.metric("Failed / stopped", counts["failed"] + counts["stopped"])
        if counts["queued"] and not counts["running"]:
            if st.button("Run queued simulations", type="primary"):
                try:
                    # Preflight the next queued simulation before creating a worker.
                    item = next(i for i in batch.items if i.status == "queued")
                    check = inspect_run(Path(item.run_dir))
                    if not check["ok"]:
                        raise ValueError("; ".join(check["errors"]))
                    start_batch(batch)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not start: {exc}")
        for item in batch.items:
            with st.expander(f"{item.name} — {item.status}", expanded=item.status in ("running", "failed")):
                st.caption(item.run_dir)
                st.write(item.message or "Not started")
                report = inspect_run(Path(item.run_dir))
                st.code(report.get("command_display", "No run command"), language="text")
                if not report["ok"]:
                    st.error("; ".join(report["errors"]))
                status = get_run_summary(Path(item.run_dir))
                st.progress(float(status["progress_fraction"]),
                            text=f"{status['completed_frames']}/{item.expected_frames} saved frames")
                if item.status == "running" and st.button(
                    "Stop this simulation", key=f"stop_{item.name}"
                ):
                    try:
                        stop_run(Path(item.run_dir))
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
                for filename in ("run.log", "run_error.log"):
                    logfile = Path(item.run_dir) / filename
                    st.markdown(f"**{filename}**")
                    if logfile.exists():
                        lines = logfile.read_text(encoding="utf-8", errors="replace").splitlines()
                        st.code("\n".join(lines[-60:]) or "(empty)", language="text")
                    else:
                        st.caption("No file yet")
    # A fragment continues polling and advancing sequential batches without
    # restarting the entire designer or requiring a manual browser refresh.
    @st.fragment(run_every="5s")
    def live_queue_status():
        latest = load_batch(bdir)
        if latest.status == "running":
            latest = advance_batch(latest)
        count = get_batch_counts(latest)
        st.caption(
            f"Live queue: {count['running']} running • {count['queued']} queued • "
            f"{count['finished']} finished • {count['failed']} failed"
        )
        for active in latest.items:
            if active.status == "running":
                summary = get_run_summary(Path(active.run_dir))
                st.progress(
                    float(summary["progress_fraction"]),
                    text=f"{active.name}: {summary['completed_frames']} / "
                    f"{active.expected_frames} frames",
                )
                st.caption(summary["message"])
    live_queue_status()
    st.caption("Running occurs in a child Python process; Streamlit terminal output can remain quiet.")
    if st.button("Refresh simulation status"):
        st.rerun()
    with st.expander("Local execution diagnostics"):
        st.write("Detected OpenMM platforms:", ", ".join(platforms))
        st.code("python -m calvados_library_builder.preflight "
                '"runs\\first_test\\test_vpgvg"')
        st.caption("Open run_error.log for Python tracebacks, run.log for CALVADOS progress, "
                   "and runner_exit_code.txt for the worker result.")


with analyze_tab:
    st.subheader("Analyze completed DCD trajectories")
    runs = run_paths()
    if not runs:
        st.info("No prepared simulations found yet.")
    else:
        target = st.selectbox(
            "Simulation", runs,
            format_func=lambda p: str(p.relative_to(ROOT)),
        )
        topology = target / "top.pdb"
        dcds = [p for p in target.glob("*.dcd") if not p.name.startswith("equilibration")]
        if not dcds:
            st.warning("No DCD trajectory found yet. Run the simulation first.")
        else:
            st.caption("Trajectory found: " + ", ".join(p.name for p in dcds))
        ac, bc = st.columns(2)
        with ac:
            stride = st.number_input("Analysis stride", 1, 10000, 1)
        with bc:
            theta_ref = st.number_input(
                "Rgθ at 420 residues (nm; Hofmann default)", min_value=0.1, max_value=20.0,
                value=float(THETA_REF_NM), step=0.001, format="%.4f",
            )
        st.caption(
            "Collapsed = Rg < Rgθ(N), with Rgθ(N) = Rgθ(420) × "
             "sqrt((N−1)/419), where the default follows √(2 × 0.40 nm × 0.38 nm × (N−1) / 6). Rates count state transitions per nanosecond "
            "in the originating state."
        )
        if st.button("Analyze selected trajectory", type="primary", disabled=not dcds):
            try:
                result = analyze_run(target, stride=int(stride), theta_ref_nm=float(theta_ref))
                st.success(f"Analyzed {result['n_frames']} frames, saved results in {target / 'analysis'}")
            except Exception as exc:
                st.error(f"Analysis failed: {exc}")
                st.caption("Analysis requires a complete readable DCD and a matching single-chain PDB.")
        summary_file = target / "analysis" / "summary.csv"
        if summary_file.exists():
            result = pd.read_csv(summary_file).drop(columns=["std_rg_nm", "iqr_rg_nm"], errors="ignore").iloc[0]
            a, b, c, d = st.columns(4)
            a.metric("Mean Rg", f"{result['mean_rg_nm']:.2f} nm")
            b.metric("Collapsed", f"{result['fraction_collapsed']:.1%}")
            c.metric("k collapse", f"{result['k_collapse_per_ns']:.3g} /ns")
            d.metric("k escape", f"{result['k_escape_per_ns']:.3g} /ns")
            st.caption(
                f"Rg theta = {result['rg_theta_nm']:.3f} nm • "
                f"{int(result['n_frames'])} sampled frames • "
                f"{result['sample_dt_ns']:.4g} ns per analyzed frame."
            )
            p1, p2 = st.columns(2)
            with p1:
                picture = target / "analysis" / "rg_time.png"
                if picture.exists():
                    st.image(str(picture), caption="Rg trajectory")
            with p2:
                picture = target / "analysis" / "rg_distribution.png"
                if picture.exists():
                    st.image(str(picture), caption="Rg distribution")
            st.download_button(
                "Download analysis summary CSV",
                pd.DataFrame([result]).to_csv(index=False).encode("utf-8"), file_name=f"{target.name}_rg_summary.csv",
                mime="text/csv",
            )
            st.dataframe(pd.DataFrame([result]), use_container_width=True)
    st.divider()
    st.subheader("Compare analyzed sequences")
    summary_files = [p / "analysis" / "summary.csv" for p in runs]
    summary_files = [p for p in summary_files if p.is_file()]
    if summary_files:
        table = pd.concat((pd.read_csv(p) for p in summary_files), ignore_index=True)
        table = table.drop(columns=["std_rg_nm", "iqr_rg_nm"], errors="ignore")
        cols = ["name", "temperature_K", "mean_rg_nm", "rg_theta_nm",
                "fraction_collapsed", "k_collapse_per_ns", "k_escape_per_ns",
                "mean_rg_collapsed_nm", "mean_rg_expanded_nm", "n_frames"]
        st.dataframe(table[[c for c in cols if c in table.columns]], use_container_width=True)
        metric = st.selectbox("Comparison metric", [
            "mean_rg_nm", "fraction_collapsed",
            "k_collapse_per_ns", "k_escape_per_ns",
            "mean_rg_collapsed_nm", "rg_relative_theta",
        ])
        st.bar_chart(table.set_index("name")[[metric]])
        st.download_button(
            "Download comparison CSV", table.to_csv(index=False),
            file_name="elp_library_summary.csv", mime="text/csv",
        )
    else:
        st.caption("Analyze one or more trajectories to see cross-sequence comparisons here.")

st.divider()
st.caption("Original detailed designer: run `python -m streamlit run legacy_app.py`. "
           "Simulation rates from short trajectories are descriptive, not equilibrium estimates.")
