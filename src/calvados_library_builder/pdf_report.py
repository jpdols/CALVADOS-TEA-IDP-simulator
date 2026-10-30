"""Publication-style multi-sequence PDF overview of local CALVADOS analyses.

Designed for an existing `runs/<batch>/<sequence>/analysis/summary.csv`
collection. Reuses the actual simulated FASTA sequence where possible and
uses the thesis motif palette for architecture diagrams.
"""
from __future__ import annotations

from collections import Counter
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Rectangle
import numpy as np
import pandas as pd

from .motifs import Motif, get_default_motifs

METRICS = [
    ("fraction_collapsed", "Fraction collapsed", "Fraction"),
    ("mean_rg_nm", "Mean Rg", "nm"),
    ("mean_rg_collapsed_nm", "Mean compact Rg", "nm"),
    ("k_collapse_per_ns", "Collapse rate", "ns⁻¹"),
    ("k_escape_per_ns", "Escape rate", "ns⁻¹"),
]


def motif_runs(sequence: str, motifs: dict[str, Motif]) -> list[tuple[str, int]]:
    """Longest-first exact segmentation, retaining all unmatched residues."""
    by_length = sorted(motifs.values(), key=lambda m: (-len(m.sequence), m.name))
    runs: list[tuple[str, int]] = []
    pos = 0
    while pos < len(sequence):
        match = next((m for m in by_length if sequence.startswith(m.sequence, pos)), None)
        if match:
            label, size = match.name, len(match.sequence)
        else:
            label, size = "Other", 1
        if runs and runs[-1][0] == label:
            old, count = runs[-1]
            runs[-1] = (old, count + 1)
        else:
            runs.append((label, 1))
        pos += size
    return runs


def _format_metric(value: object, key: str) -> str:
    try:
        number = float(value)
    except (ValueError, TypeError):
        return "—"
    if not np.isfinite(number):
        return "—"
    if key == "fraction_collapsed":
        return f"{number * 100:.1f}%"
    return f"{number:.3f}" if abs(number) >= 0.01 else f"{number:.2g}"


def _draw_architecture(ax, sequence: str, motifs: dict[str, Motif], x: float, y: float,
                       max_width: float = 0.38) -> None:
    runs = motif_runs(sequence, motifs)
    if not runs:
        ax.text(x, y, "No sequence", transform=ax.transAxes, fontsize=7, color="#666")
        return
    shown = runs[:16]
    step = min(0.025, max_width / max(1, len(shown)))
    cursor = x
    for label, count in shown:
        color = motifs[label].color if label in motifs else "#AAAAAA"
        ax.add_patch(Circle((cursor + step*.46, y), min(step*.28, .008),
                            color=color, ec="#FFFFFF", lw=.35,
                            transform=ax.transAxes, clip_on=False))
        ax.text(cursor + step*.46, y - .019, f"×{count}",
                ha="center", va="top", fontsize=6.4,
                transform=ax.transAxes, color="#444")
        cursor += step
    if len(runs) > len(shown):
        ax.text(min(x+max_width, cursor), y, f"+{len(runs)-len(shown)} blocks",
                fontsize=6.5, transform=ax.transAxes, color="#555")


def _overview(pdf: PdfPages, frame: pd.DataFrame, motifs: dict[str, Motif]) -> None:
    per_page = 11
    n_pages = (len(frame) + per_page - 1) // per_page
    for page in range(n_pages):
        data = frame.iloc[page*per_page:(page+1)*per_page]
        fig = plt.figure(figsize=(16.5, 11.7), facecolor="white")
        ax = fig.add_axes([.035, .075, .93, .79])
        ax.axis("off")
        fig.text(.045, .945, "ELP  /  ARCHITECTURE & COMPACTION",
                 fontsize=22, fontweight="bold", color="#172334")
        fig.text(.045, .91, "CALVADOS trajectory analysis  •  grouped motif architectures and state kinetics",
                 fontsize=10, color="#667085")
        xloc = [.01, .18, .59, .70, .79, .88, .955]
        heads = ["Design", "Motif architecture", "Collapsed", "Mean Rg", "Compact Rg",
                 "k collapse", "k escape"]
        for col, label in zip(xloc, heads):
            ax.text(col, 1.017, label, transform=ax.transAxes, fontsize=9,
                    color="#475467", weight="bold", va="bottom")
        for i, (_, row) in enumerate(data.iterrows()):
            yy = 0.955 - i*.078
            ax.add_patch(Rectangle((0, yy-.049), 1, .073, transform=ax.transAxes,
                                   facecolor="#F4F7FA" if i % 2 == 0 else "#FFFFFF",
                                   edgecolor="none"))
            name = str(row.get("name", f"Sequence {i+1}"))
            if len(name) > 26:
                name = name[:23] + "..."
            ax.text(xloc[0], yy, name, transform=ax.transAxes, fontsize=8.0,
                    va="center", weight="bold", color="#172334")
            _draw_architecture(ax, str(row.get("sequence", "") or ""), motifs, xloc[1], yy+.006)
            for x, (key, _, _) in zip(xloc[2:], METRICS):
                ax.text(x, yy, _format_metric(row.get(key), key),
                        transform=ax.transAxes, fontsize=8.3, va="center", color="#172334")
        fig.text(.045, .045, "Created by Joep Dols  ·  Nikolina Šoštarić Lab  ·  TU Delft",
                 fontsize=8, color="#667085")
        fig.text(.955, .045, f"Overview {page+1} / {n_pages}",
                 fontsize=8, ha="right", color="#667085")
        pdf.savefig(fig)
        plt.close(fig)


def _metric_panels(pdf: PdfPages, frame: pd.DataFrame) -> None:
    for start in range(0, len(METRICS), 2):
        fig, axes = plt.subplots(2, 1, figsize=(16.5, 11.7), facecolor="white")
        fig.suptitle("ELP  /  QUANTITATIVE COMPARISON", x=.07, ha="left", y=.965,
                     fontweight="bold", fontsize=20, color="#172334")
        for ax, metric in zip(axes, METRICS[start:start+2]):
            key, title, unit = metric
            subset = frame[["name", key]].copy()
            subset[key] = pd.to_numeric(subset[key], errors="coerce")
            subset = subset.dropna(subset=[key])
            subset = subset.sort_values(key, kind="stable")
            ax.set_title(title, loc="left", fontsize=14, fontweight="bold", pad=13)
            if subset.empty:
                ax.text(.5, .5, "No finite results", ha="center", va="center",
                        transform=ax.transAxes)
            else:
                # Landscape report: show up to 30 sequences per plot. CSV holds all.
                subset = subset.tail(30)
                yp = np.arange(len(subset))
                bars = ax.barh(yp, subset[key].to_numpy(), color="#4C78A8",
                               edgecolor="white", height=.7)
                ax.set_yticks(yp, labels=subset.name.tolist(), fontsize=8)
                ax.tick_params(axis="x", labelsize=9)
                ax.grid(axis="x", alpha=.14)
                ax.set_axisbelow(True)
                ax.set_xlabel(unit, fontsize=10)
            ax.spines[["top", "right", "left"]].set_visible(False)
        if start+1 >= len(METRICS):
            axes[-1].axis("off")
        fig.tight_layout(rect=[.045, .06, .97, .92], h_pad=3)
        fig.text(.05, .03, "Rates are transitions per unit state exposure time; assess sampling and equilibration before interpreting differences.",
                 color="#667085", fontsize=8)
        pdf.savefig(fig)
        plt.close(fig)


def export_comparison_pdf(frame: pd.DataFrame, *,
                          motifs: dict[str, Motif] | None = None) -> bytes:
    """Return PDF bytes without touching analyzed trajectories."""
    if frame.empty:
        raise ValueError("Analyze at least one sequence before exporting.")
    missing = {key for key, _, _ in METRICS} - set(frame.columns)
    if missing:
        raise ValueError(f"Missing analysis columns: {', '.join(sorted(missing))}")
    if "name" not in frame.columns or "sequence" not in frame.columns:
        raise ValueError("Analysis comparison requires name and exact sequence columns.")
    motifs = motifs or get_default_motifs()
    buffer = BytesIO()
    with PdfPages(buffer, metadata={
        "Title": "ELP Architecture and CALVADOS Analysis",
        "Author": "Joep Dols — Nikolina Šoštarić Lab, TU Delft",
    }) as pdf:
        _overview(pdf, frame.reset_index(drop=True), motifs)
        _metric_panels(pdf, frame.reset_index(drop=True))
    return buffer.getvalue()
