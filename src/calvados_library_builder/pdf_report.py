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


# Large A3 landscape pages preserve the grouping language of the sequence
# designer: a colored circle, a light count, a bracket, then a bold count and
# an explicit motif label. All geometry is vector PDF content.
OVERVIEW_BLOCKS = 10
OVERVIEW_ROWS = 5
DETAIL_COLUMNS = 12
DETAIL_ROWS = 5
DESIGN_COLORS = (
    "#4275A8", "#D6A73E", "#529E7A", "#9A70AA",
    "#CF755B", "#4C9AA3", "#7286A9",
)


def _draw_group(ax, label: str, count: int, motifs: dict[str, Motif],
                cx: float, cy: float, slot: float = .060) -> None:
    """Draw one contiguous motif group using the Studio's annotated-circle style.

    Scatter marker sizes are in points rather than axes units, so circles
    stay circular even on an A3 landscape page.
    """
    color = motifs[label].color if label in motifs else "#A5ACB7"
    name = motifs[label].display_label if label in motifs else label
    ax.scatter([cx], [cy + .038], s=150, c=[color], edgecolors="#C1CBD5",
               linewidths=.55, transform=ax.transAxes, zorder=4, clip_on=False)
    ax.text(cx, cy + .009, f"×{count}", ha="center", va="center",
            fontsize=7.1, color="#8390A3", transform=ax.transAxes)
    half = min(slot * .32, .025)
    bracket_y = cy - .021
    ax.plot([cx-half, cx+half], [bracket_y, bracket_y],
            color="#A1ABBA", lw=.7, transform=ax.transAxes, clip_on=False)
    for side in (-1, 1):
        ax.plot([cx+side*half, cx+side*half],
                [bracket_y, bracket_y + .010], color="#A1ABBA",
                lw=.7, transform=ax.transAxes, clip_on=False)
    ax.text(cx, cy - .041, f"×{count}", ha="center", va="center",
            fontsize=8.5, fontweight="bold", color="#1D2A3A",
            transform=ax.transAxes)
    ax.text(cx, cy - .064, name, ha="center", va="center",
            fontsize=6.9 if len(name) > 8 else 7.7, color="#778498",
            transform=ax.transAxes)


def _draw_architecture(ax, sequence: str, motifs: dict[str, Motif],
                       x: float, y: float, max_width: float = .415) -> int:
    """Show up to ten groups in the overview and return total group count.

    Longer architectures receive full-resolution detail pages, not an
    untraceable '+41 blocks' ending.
    """
    runs = motif_runs(sequence, motifs)
    if not runs:
        ax.text(x, y, "No sequence", transform=ax.transAxes,
                fontsize=9, color="#667085")
        return 0
    shown = runs[:OVERVIEW_BLOCKS]
    slot = min(.077, max_width / len(shown))
    for j, (name, count) in enumerate(shown):
        _draw_group(ax, name, count, motifs,
                    x + (j+.5)*slot, y, slot=slot)
    if len(runs) > OVERVIEW_BLOCKS:
        ax.text(x, y - .086,
                f"First {OVERVIEW_BLOCKS} of {len(runs)} groups  ·  full map on detail page",
                ha="left", va="center", fontsize=7.1,
                color="#546A88", transform=ax.transAxes)
    return len(runs)


def _page_footer(fig, text: str, page_label: str) -> None:
    fig.text(.046, .045, text, fontsize=8, color="#667085")
    fig.text(.954, .045, page_label, fontsize=8, ha="right",
             color="#667085")


def _motif_legend(fig, data: pd.DataFrame, motifs: dict[str, Motif]) -> None:
    used: list[str] = []
    for seq in data["sequence"].fillna("").astype(str):
        for name, _ in motif_runs(seq, motifs):
            if name not in used:
                used.append(name)
    for j, name in enumerate(used):
        row, col = divmod(j, 8)
        if row >= 2:
            break
        xx, yy = .047 + col*.117, .870 - row*.026
        color = motifs[name].color if name in motifs else "#A5ACB7"
        label = motifs[name].display_label if name in motifs else name
        fig.text(xx, yy, "●", fontsize=13.5, color=color, va="center")
        fig.text(xx+.016, yy, label, fontsize=8, color="#667085",
                 va="center")


def _overview(pdf: PdfPages, frame: pd.DataFrame, motifs: dict[str, Motif]) -> None:
    n_pages = (len(frame) + OVERVIEW_ROWS - 1) // OVERVIEW_ROWS
    for page in range(n_pages):
        data = frame.iloc[page*OVERVIEW_ROWS:(page+1)*OVERVIEW_ROWS]
        fig = plt.figure(figsize=(16.5, 11.7), facecolor="white")
        ax = fig.add_axes([.037, .092, .924, .696])
        ax.set(xlim=(0, 1), ylim=(0, 1))
        ax.axis("off")
        fig.text(.047, .944, "ELP  /  ARCHITECTURE & COMPACTION",
                 fontsize=21, fontweight="bold", color="#172334")
        fig.text(.047, .910, "CALVADOS trajectory analysis  /  grouped motifs  /  state kinetics",
                 fontsize=10, color="#667085")
        _motif_legend(fig, data, motifs)
        ax.text(.012, 1.018, "DESIGN", weight="bold", fontsize=9,
                color="#475467", transform=ax.transAxes)
        ax.text(.174, 1.018, "CONTIGUOUS MOTIF GROUPS", weight="bold",
                fontsize=9, color="#475467", transform=ax.transAxes)
        headers = [
            (.647, "Collapsed"),
            (.726, "Mean Rg"),
            (.808, "Compact Rg"),
            (.887, "k collapse"),
            (.965, "k escape"),
        ]
        for xx, label in headers:
            ax.text(xx, 1.018, label, ha="center", weight="bold",
                    fontsize=8.5, color="#475467", transform=ax.transAxes)
        for i, (_, row) in enumerate(data.iterrows()):
            center = .885 - i*.171
            ax.add_patch(Rectangle((.004, center-.098), .992, .164,
                                   facecolor="#F5F7FA" if i%2==0 else "#FFFFFF",
                                   edgecolor="none", transform=ax.transAxes,
                                   zorder=0))
            name = str(row.get("name", f"Sequence {i+1}"))
            short_name = name if len(name)<=23 else name[:20]+"..."
            ax.text(.012, center+.020, short_name, ha="left", va="center",
                    weight="bold", fontsize=9.0, color="#172334",
                    transform=ax.transAxes)
            seq = str(row.get("sequence", "") or "")
            temp = pd.to_numeric(row.get("temperature_K"), errors="coerce")
            temp_note = f"  ·  {temp:g} K" if pd.notna(temp) else ""
            ax.text(.012, center-.016, f"N = {len(seq)} aa{temp_note}",
                    fontsize=8, color="#667085", va="center",
                    transform=ax.transAxes)
            _draw_architecture(ax, seq, motifs, .172, center)
            for (xx, _), (key, _, _) in zip(headers, METRICS):
                ax.text(xx, center+.006, _format_metric(row.get(key), key),
                        ha="center", va="center", fontsize=9,
                        color="#172334", transform=ax.transAxes)
        _page_footer(fig,
                     "Each circle = one contiguous group; ×n = consecutive motif copies. Long architectures are reproduced in full.",
                     f"Overview {page+1} / {n_pages}")
        pdf.savefig(fig)
        plt.close(fig)


def _architecture_details(pdf: PdfPages, frame: pd.DataFrame,
                          motifs: dict[str, Motif]) -> None:
    """Reproduce EVERY contiguous block for longer sequences, in sequence order."""
    block_capacity = DETAIL_COLUMNS*DETAIL_ROWS
    for _, record in frame.iterrows():
        seq = str(record["sequence"] or "")
        runs = motif_runs(seq, motifs)
        if len(runs) <= OVERVIEW_BLOCKS:
            continue
        n_pages = (len(runs) + block_capacity - 1)//block_capacity
        for page in range(n_pages):
            chunk = runs[page*block_capacity:(page+1)*block_capacity]
            fig = plt.figure(figsize=(16.5, 11.7), facecolor="white")
            ax = fig.add_axes([.048, .112, .904, .698])
            ax.set(xlim=(0,1), ylim=(0,1))
            ax.axis("off")
            name = str(record.get("name", "Sequence"))
            fig.text(.048, .941, "ELP  /  FULL MOTIF ARCHITECTURE",
                     fontsize=21, fontweight="bold", color="#172334")
            fig.text(.048, .897,
                     f"{name}   ·   {len(seq)} amino acids   ·   {len(runs)} contiguous groups",
                     fontsize=11.2, color="#546A88")
            fig.text(.048, .867,
                     "Groups appear left-to-right and then top-to-bottom in sequence order.",
                     fontsize=9, color="#667085")
            step = .972 / DETAIL_COLUMNS
            for index, (label, count) in enumerate(chunk):
                rr, cc = divmod(index, DETAIL_COLUMNS)
                x = .014 + (cc+.5)*step
                y = .884 - rr*.178
                _draw_group(ax, label, count, motifs, x, y, slot=step)
            _page_footer(fig,
                         "Each circle = one contiguous group; both labels show the number of consecutive motifs.",
                         f"Architecture {page+1} / {n_pages}")
            pdf.savefig(fig)
            plt.close(fig)


def _metric_panels(pdf: PdfPages, frame: pd.DataFrame) -> None:
    """Compact comparison for small libraries, readable pagination for large ones."""
    small_library = len(frame) <= 8
    per_page = 6 if small_library else 2
    for start in range(0, len(METRICS), per_page):
        if small_library:
            fig, axes = plt.subplots(3, 2, figsize=(16.5, 11.7),
                                     facecolor="white")
        else:
            fig, axes = plt.subplots(2, 1, figsize=(16.5, 11.7),
                                     facecolor="white")
        axes_list = np.asarray(axes).ravel()
        fig.suptitle("ELP  /  QUANTITATIVE COMPARISON", x=.077, ha="left",
                     y=.956, fontweight="bold", fontsize=20, color="#172334")
        for ax, (key, title, unit) in zip(axes_list, METRICS[start:start+per_page]):
            # Preserve overview order across every panel.
            subset = frame[["name", key]].copy()
            subset[key] = pd.to_numeric(subset[key], errors="coerce")
            subset["_design_idx"] = np.arange(len(subset))
            subset = subset[np.isfinite(subset[key])].head(30)
            ax.set_title(title, loc="left", fontsize=12.2, fontweight="bold", pad=10)
            if subset.empty:
                ax.text(.5, .5, "No finite results", ha="center", va="center",
                        transform=ax.transAxes, color="#667085")
            else:
                values = subset[key].to_numpy(dtype=float)
                colors = [DESIGN_COLORS[int(i)%len(DESIGN_COLORS)]
                          for i in subset["_design_idx"]]
                yp = np.arange(len(subset))
                bars = ax.barh(yp, values, color=colors, height=.65)
                labels = [str(n) if len(str(n)) <= 22 else str(n)[:19]+"..."
                          for n in subset["name"]]
                ax.set_yticks(yp, labels=labels, fontsize=8.4)
                ax.invert_yaxis()
                positive_max = max(0., float(np.max(values)))
                ax.set_xlim(0, positive_max*1.22 if positive_max else 1)
                ax.bar_label(bars,
                             labels=[_format_metric(v, key) for v in values],
                             padding=3, fontsize=8, color="#344054")
                ax.grid(axis="x", alpha=.13)
                ax.set_axisbelow(True)
            ax.tick_params(axis="x", labelsize=8.4)
            ax.tick_params(axis="y", length=0)
            ax.set_xlabel(unit, fontsize=9.2)
            ax.spines[["top", "right", "left"]].set_visible(False)
        for ax in axes_list[len(METRICS[start:start+per_page]):]:
            ax.axis("off")
        if small_library:
            fig.subplots_adjust(left=.135, right=.965, top=.875,
                                bottom=.108, hspace=.55, wspace=.43)
        else:
            fig.subplots_adjust(left=.13, right=.965, top=.87,
                                bottom=.10, hspace=.38)
        fig.text(.077, .045,
                 "Bar colors identify designs across panels. Rates depend on state exposure and transition sampling; interpret with care.",
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
