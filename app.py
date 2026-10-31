"""CALVADOS ELP Studio — design, simulate and analyze without a long configuration form.

Advanced original UI: streamlit run legacy_app.py
"""
from __future__ import annotations

from pathlib import Path
from html import escape
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
from calvados_library_builder.config import RUNS_DIR, SimulationConfig, SUPPORTED_PLATFORMS
from calvados_library_builder.designs import Candidate, make_library, simple_elp, validate_sequence
from calvados_library_builder.diagnostics import available_platforms
from calvados_library_builder.preflight import inspect_run
from calvados_library_builder.prepare import prepare_simulation
from calvados_library_builder.runner import get_run_summary, stop_run
from calvados_library_builder.bulk_import import parse_sequence_library
from calvados_library_builder.design_collection import (
    add_to_collection, remove_from_collection, next_design_name,
    save_collection, load_collection,
)
from calvados_library_builder.pdf_report import export_comparison_pdf
from calvados_library_builder.replicate_summary import summarize_replicates
from calvados_library_builder.replicates import (
    build_run_plan, validate_run_plan, write_replicate_info, experiment_from_path,
)
from calvados_library_builder.motifs import get_default_motifs, create_motif
from calvados_library_builder.motif_canvas import motif_canvas
from calvados_library_builder.studio_sequence import (
    default_groups, groups_to_sequence, groups_to_architecture,
    count_motifs, normalize_groups, extract_single_fasta,
    segment_raw_sequence, load_custom_motifs, save_custom_motifs,
    load_draft, save_draft,
)


st.set_page_config(page_title="ELP Studio", page_icon="🧬", layout="wide")
# Optional artwork extracted from the user's original scanned PDF.
# The tracked image lives in assets/elp_header.jpg; the dashboard stays functional without it.
header_art = Path(__file__).resolve().parent / "assets" / "elp_header.jpg"
header_title, header_illustration = st.columns([5, 2], vertical_alignment="center")
with header_title:
    st.title("ELP Studio")
    st.caption("Design an IDP/ELP • simulate using CALVADOS-TEA • analyze results")
with header_illustration:
    if header_art.is_file():
        st.image(str(header_art), width=250)
st.markdown(
    """
    <style>
    html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"],
    [data-testid="stWidgetLabel"], button, input, textarea {
        font-family: "Suisse Intl", "Suisse", "Helvetica Neue", Arial, sans-serif;
    }
    </style>
    """, unsafe_allow_html=True,
)
st.caption("Created by Joep Dols · Nikolina Šoštarić Lab · TU Delft")


ROOT = RUNS_DIR
ROOT.mkdir(parents=True, exist_ok=True)
platforms = available_platforms()
# Allow users to attempt any CALVADOS-supported backend. OpenMM's platform
# listing is informative, not a gate: the child run reports the real outcome.
choices = list(SUPPORTED_PLATFORMS)


def safe_label(value: str) -> str:
    label = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._")
    if not label:
        raise ValueError("Enter a valid name.")
    return label


def batch_paths() -> list[Path]:
    return sorted(ROOT.glob("*/batch_state.json"), reverse=True)


def run_paths() -> list[Path]:
    found = {p.parent for p in ROOT.glob("*/*/config.yaml")}
    found.update(p.parent for p in ROOT.glob("*/*/*/config.yaml"))
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

    # The Add & New button queues a reset for the next rerun. Streamlit does
    # not allow replacing an instantiated widget's session-state key in place.
    pending_name = st.session_state.pop("_studio_new_design_name", None)
    if pending_name is not None:
        st.session_state["studio_sequence_name"] = pending_name

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
                    f'<b>{escape(motif.name)}</b> · {escape(motif.sequence)}', unsafe_allow_html=True
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

    # Stage first; preparing CALVADOS inputs is a separate, explicit action.
    collection_path = ROOT / "_design_collection.json"
    if "studio_design_collection" not in st.session_state:
        try:
            st.session_state["studio_design_collection"] = load_collection(collection_path)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            st.session_state["studio_design_collection"] = []
            st.error(f"Could not restore saved design collection: {exc}")
    staged = st.session_state["studio_design_collection"]

    def store_design_collection(updated: list[Candidate]) -> None:
        save_collection(collection_path, updated)
        st.session_state["studio_design_collection"] = updated

    st.divider()
    st.subheader("2. Add designs to your experiment")
    st.caption(
        "Add your current ELP to a collection, then design another. "
        "Nothing is prepared or simulated until you click Prepare all below. "
        "Your collection is saved between application sessions."
    )
    add_col, next_col = st.columns(2)
    with add_col:
        if st.button("Add current design", type="primary", disabled=not candidates):
            try:
                updated = add_to_collection(staged, candidates)
                store_design_collection(updated)
                st.success(f"Added {candidates[0].name} to the experiment collection.")
                st.rerun()
            except (ValueError, OSError) as exc:
                st.error(f"Could not add design: {exc}")
    with next_col:
        if st.button("Add current & design another", disabled=not candidates):
            try:
                updated = add_to_collection(staged, candidates)
                store_design_collection(updated)
                st.session_state["_studio_new_design_name"] = next_design_name(updated)
                st.session_state["studio_groups"] = []
                st.session_state["studio_canvas_revision"] += 1
                st.rerun()
            except (ValueError, OSError) as exc:
                st.error(f"Could not add design: {exc}")

    with st.expander("Import several existing sequences at once (FASTA / CSV)"):
        st.caption("Add an existing sequence library directly to the same collection, without using the motif editor.")
        upload = st.file_uploader(
            "Multi-FASTA or CSV library", type=["fasta", "fa", "faa", "txt", "csv"],
            key="studio_library_upload",
            help="FASTA has >NAME headers; CSV requires name and sequence columns.",
        )
        pasted_library = st.text_area(
            "Or paste multi-FASTA", key="studio_multi_fasta", height=120,
            placeholder=">ELP_01\\nVPGVGVPGVG\\n>ELP_02\\nVPGVGIPAVG",
        )
        if st.button("Add imported sequences to collection", disabled=upload is None and not pasted_library.strip()):
            try:
                if upload is not None:
                    contents = upload.getvalue().decode("utf-8-sig")
                    filename = upload.name
                else:
                    contents = pasted_library
                    filename = "pasted.fasta"
                new_designs = parse_sequence_library(contents, filename=filename)
                updated = add_to_collection(staged, new_designs)
                store_design_collection(updated)
                st.success(f"Added {len(new_designs)} sequences to your collection.")
                st.rerun()
            except (UnicodeDecodeError, ValueError, OSError) as exc:
                st.error(f"Import failed: {exc}")

    staged = st.session_state["studio_design_collection"]
    st.markdown(f"**Designs ready to prepare: {len(staged)}**")
    if staged:
        preview(staged)
        st.download_button(
            "Download staged collection FASTA",
            data="".join(f">{c.name}\n{c.sequence}\n" for c in staged),
            file_name="elp_staged_designs.fasta",
            mime="text/plain",
        )
        selected_remove = st.selectbox(
            "Remove a design from collection", [c.name for c in staged],
            key="studio_remove_design_name",
        )
        remove_col, clear_col = st.columns(2)
        with remove_col:
            if st.button("Remove selected design"):
                try:
                    store_design_collection(remove_from_collection(staged, selected_remove))
                    st.rerun()
                except (ValueError, OSError) as exc:
                    st.error(f"Could not remove design: {exc}")
        with clear_col:
            if st.button("Clear collection", help="Clears staged designs only; existing prepared simulations are not deleted."):
                try:
                    store_design_collection([])
                    st.rerun()
                except OSError as exc:
                    st.error(f"Could not clear collection: {exc}")
    else:
        st.info("Your collection is empty. Add your first design above.")

    candidates = staged

    st.divider()
    st.subheader("3. Prepare all simulations")
    st.caption("The entire staged collection will use these settings. You can keep adding designs until you are ready; no existing run folders are overwritten.")
    batch_name = st.text_input("Experiment name", "first_test")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        temperature = st.selectbox("Temperature (K)", list(range(300, 401, 10)), index=7, help="Simulation temperature in kelvin. The CALVADOS residue interaction table is temperature-dependent; choose the temperature of the desired experiment.")
    with s2:
        platform = st.selectbox(
            "Compute", choices,
            help="Try CPU or CUDA. CUDA requires an OpenMM CUDA platform plus "
                 "a compatible NVIDIA GPU/driver. CUDA remains selectable "
                 "even when the initial OpenMM check does not detect it.",
        )
        if platform == "CUDA" and "CUDA" not in platforms:
            st.warning(
                "CUDA is not currently listed among the OpenMM platforms "
                f"({', '.join(platforms)}). You may still prepare and try "
                "a CUDA run; if it cannot initialize, check run_error.log. "
                "Use a new experiment name to protect existing results."
            )
    with s3:
        frames = st.number_input("Saved frames", 2, 50000, 50, help="How many trajectory configurations to save in the DCD. More frames provide better temporal sampling but larger files. Total steps = frames × steps per frame.")
    with s4:
        save_every = st.number_input("Steps per frame", 1, 1000000, 1000, help="OpenMM integration steps between saved trajectory frames. CALVADOS uses a 0.01 ps step: 1000 steps = 10 ps = 0.01 ns between frames.")
    with st.expander("Advanced simulation settings"):
        box_nm = st.number_input("Box length (nm)", 5.0, 500.0, 50.0, help="Side length of the periodic cubic simulation box in nanometers. It must comfortably contain the polymer and avoid unwanted interactions with periodic images.")
        ph = st.number_input("pH", 0.0, 14.0, 7.0, help="Solution pH. Affects residue protonation / effective charge and therefore electrostatic interactions according to the CALVADOS model.")
        ionic = st.number_input("Ionic strength (M)", 0.0, 5.0, 0.17, help="Ionic strength in mol/L. Controls Debye electrostatic screening; higher salt generally screens charge interactions more strongly.")
        first_seed = st.number_input("Starting random seed", 0, 2147483646, 1, help="Random number seed for reproducibility. In a library, each successive sequence receives an incremented seed. Use different seeds for independent replicate runs.")
    triplicate = st.toggle(
        "Run in triplicate (3 independent replicates)",
        value=False,
        help="Prepare 3 independent simulations per sequence, with different seeds. "
             "Each replicate has its own DCD, checkpoint, log and analysis folder.",
    )
    count_reps = 3 if triplicate else 1
    st.caption(
        f"{int(frames) * int(save_every):,} integration steps per run · "
        f"{len(candidates)} sequence(s) × {count_reps} replicate(s) "
        f"= {len(candidates) * count_reps} independent run(s)."
    )
    if st.button("Prepare all staged designs", type="primary", disabled=not candidates):
        try:
            # Preflight every intended destination before preparing any files.
            experiment_dir = choose_batch_name(batch_name)
            plan = build_run_plan(
                candidates, experiment_dir,
                triplicate=bool(triplicate), first_seed=int(first_seed),
            )
            existing = (
                load_batch(experiment_dir)
                if (experiment_dir / "batch_state.json").exists() else None
            )
            validate_run_plan(plan, existing.items if existing else ())
            b = existing if existing else create_batch(safe_label(batch_name), experiment_dir)
            prepared = []
            for item in plan:
                cfg = SimulationConfig(
                    name=item.simulation_name, sequence=item.sequence,
                    temperature=float(temperature), pH=float(ph),
                    ionic_strength=float(ionic), box_size=float(box_nm),
                    n_frames=int(frames), save_every=int(save_every),
                    platform=platform, seed=item.seed, replicate=item.replicate,
                )
                run = prepare_simulation(cfg, batch_dir=item.batch_dir)
                write_replicate_info(item, safe_label(batch_name))
                b = add_simulation(b, item.simulation_name, run, int(frames))
                prepared.append(item.simulation_name)
            st.success(
                f"Prepared {len(prepared)} independent run(s) in '{b.name}'. "
                "Open Simulate to start."
            )
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
        discard_first_10 = st.toggle(
            "Discard first 10% of trajectory frames (equilibration)",
            value=False,
            key="discard_first_ten_percent",
            help="Exclude floor(10% × total original DCD frames) before striding, "
                 "Rg statistics and transition counting. The excluded portion "
                 "will not contribute to any metric or saved plot.",
        )
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
                result = analyze_run(
                    target, stride=int(stride), theta_ref_nm=float(theta_ref),
                    discard_fraction=0.1 if discard_first_10 else 0.0,
                )
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
                f"{int(result.get('discarded_frames', 0))} discarded • "
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
    analyzed_runs = [p for p in runs if (p / "analysis" / "summary.csv").is_file()]
    experiments = sorted({experiment_from_path(p, ROOT) for p in analyzed_runs})
    experiment_filter = st.selectbox(
        "Experiment to compare",
        ["All experiments", *experiments],
        index=1 if len(experiments) == 1 else 0,
        help="Restrict the plots and PDF report to one experiment (batch). "
             "Choose All experiments for a cross-batch comparison.",
    ) if experiments else "All experiments"
    comparison_runs = [
        p for p in analyzed_runs
        if experiment_filter == "All experiments" or experiment_from_path(p, ROOT) == experiment_filter
    ]
    summary_files = [p / "analysis" / "summary.csv" for p in comparison_runs]
    if summary_files:
        table = pd.concat((pd.read_csv(p) for p in summary_files), ignore_index=True)
        table = table.drop(columns=["std_rg_nm", "iqr_rg_nm"], errors="ignore")
        cols = ["name", "temperature_K", "mean_rg_nm", "rg_theta_nm",
                "fraction_collapsed", "k_collapse_per_ns", "k_escape_per_ns",
                "mean_rg_collapsed_nm", "mean_rg_expanded_nm", "n_frames"]
        st.dataframe(table[[c for c in cols if c in table.columns]], use_container_width=True)
        aggregate = summarize_replicates(table)
        if not aggregate.empty and (aggregate["n_replicates"] > 1).any():
            st.markdown("**Replicate-averaged results**")
            st.caption(
                "Each replicate is analyzed independently. Values below are means "
                "and between-replicate standard deviations; frames are not pooled. "
                "Apply the same equilibration discard to each replicate before comparing."
            )
            st.dataframe(aggregate, use_container_width=True, hide_index=True)
            st.download_button(
                "Download replicate-averaged CSV",
                aggregate.to_csv(index=False), "elp_replicate_averages.csv",
                mime="text/csv",
            )
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
        st.subheader("Export thesis-style comparison report")
        st.caption(
            "Landscape PDF with motif-ball architectures and five metric plots: "
            "fraction collapsed, mean Rg, mean compact Rg, k collapse and k escape. "
            "Results are taken from existing summary CSVs; missing metrics remain unreported."
        )
        if st.button("Generate comparison PDF", type="primary"):
            try:
                report_motifs = {
                    **get_default_motifs(), **load_custom_motifs(ROOT / "_custom_motifs.json")
                }
                report_bytes = export_comparison_pdf(table, motifs=report_motifs)
                st.session_state["studio_comparison_pdf"] = report_bytes
                st.success("Comparison PDF is ready.")
            except Exception as exc:
                st.error(f"Could not produce comparison PDF: {exc}")
        if st.session_state.get("studio_comparison_pdf"):
            st.download_button(
                "Download comparison PDF",
                data=st.session_state["studio_comparison_pdf"],
                file_name="ELP_thesis_architecture_comparison.pdf",
                mime="application/pdf",
            )
    else:
        st.caption("Analyze one or more trajectories to see cross-sequence comparisons here.")

st.divider()
st.caption("Simulation rates from short trajectories are descriptive, not equilibrium estimates.")
