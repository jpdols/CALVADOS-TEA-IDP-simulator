"""Local CALVADOS trajectory analysis matching the thesis's two-state definitions.

Outputs all_rg_values.csv, summary.csv, Rg vs time and distribution PNGs,
and methods.json. A completed DCD + PDB and FASTA are required.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

TIMESTEP_PS = 0.01  # CALVADOS 0.9.1 Langevin integrator
# Hofmann theta-state ideal-chain reference: lp*=0.40 nm, b=0.38 nm.
# N is the number of amino acids; N-1 is the number of backbone bonds.
THETA_PERSISTENCE_LENGTH_NM = 0.40
THETA_BOND_LENGTH_NM = 0.38
THETA_REF_LENGTH = 420
THETA_EXPONENT = 0.5
THETA_REF_NM = math.sqrt(
    2 * THETA_PERSISTENCE_LENGTH_NM * THETA_BOND_LENGTH_NM
    * (THETA_REF_LENGTH - 1) / 6
)


def theta_rg(n: int, reference_nm: float = THETA_REF_NM,
             reference_length: int = THETA_REF_LENGTH,
             exponent: float = THETA_EXPONENT) -> float:
    if n < 2 or reference_length < 2 or reference_nm <= 0:
        raise ValueError("Theta model requires N>=2 and positive reference values.")
    return float(reference_nm * ((n - 1) / (reference_length - 1)) ** exponent)


def summarize_rg(rg_nm, frame_dt_ns: float, threshold_nm: float) -> dict:
    """Transition counts are adjacent-frame flips; rates use total state exposure."""
    rg = np.asarray(rg_nm, dtype=float)
    if rg.ndim != 1 or len(rg) < 2 or not np.isfinite(rg).all():
        raise ValueError("Need at least two finite Rg values.")
    if frame_dt_ns <= 0 or threshold_nm <= 0:
        raise ValueError("Frame spacing and theta threshold must be positive.")

    c = rg < threshold_nm
    transitions = np.diff(c.astype(np.int8))
    nc = int(np.sum(transitions == 1))
    ne = int(np.sum(transitions == -1))
    compact_t = float(np.sum(c) * frame_dt_ns)
    expanded_t = float(np.sum(~c) * frame_dt_ns)

    cuts = np.r_[0, np.flatnonzero(transitions) + 1, len(c)]
    lengths = np.diff(cuts) * frame_dt_ns
    labels = c[cuts[:-1]]
    # The first/last dwells are right/left censored and excluded from means.
    inner = np.zeros(len(lengths), dtype=bool)
    if len(lengths) > 2:
        inner[1:-1] = True
    cd = lengths[labels & inner]
    ed = lengths[(~labels) & inner]
    quantiles = np.percentile(rg, [5, 50, 95])

    return {
        "n_frames": int(len(rg)),
        "sample_dt_ns": float(frame_dt_ns),
        "duration_ns": float(len(rg) * frame_dt_ns),
        "rg_theta_nm": float(threshold_nm),
        "mean_rg_nm": float(np.mean(rg)),
        "median_rg_nm": float(quantiles[1]),
        "p05_rg_nm": float(quantiles[0]),
        "p95_rg_nm": float(quantiles[2]),
        "rg_range_90_nm": float(quantiles[2] - quantiles[0]),
        "rg_relative_theta": float(np.mean(rg) / threshold_nm),
        "fraction_collapsed": float(np.mean(c)),
        "mean_rg_collapsed_nm": float(np.mean(rg[c])) if c.any() else float("nan"),
        "mean_rg_expanded_nm": float(np.mean(rg[~c])) if (~c).any() else float("nan"),
        "mean_collapse_depth_nm": float(np.mean(threshold_nm - rg[c])) if c.any() else float("nan"),
        "n_collapse_transitions": nc,
        "n_escape_transitions": ne,
        "k_collapse_per_ns": float(nc / expanded_t) if expanded_t else float("nan"),
        "k_escape_per_ns": float(ne / compact_t) if compact_t else float("nan"),
        "mean_collapsed_dwell_ns": float(np.mean(cd)) if len(cd) else float("nan"),
        "mean_expanded_dwell_ns": float(np.mean(ed)) if len(ed) else float("nan"),
        "n_complete_collapsed_dwells": int(len(cd)),
        "n_complete_expanded_dwells": int(len(ed)),
    }


def locate_files(run_dir: Path):
    run_dir = Path(run_dir).resolve()
    cfg_path = run_dir / "config.yaml"
    components_path = run_dir / "components.yaml"
    if not cfg_path.exists() or not components_path.exists():
        raise FileNotFoundError("Missing config.yaml or components.yaml in selected run.")
    import yaml
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    component_cfg = yaml.safe_load(components_path.read_text(encoding="utf-8"))
    systems = component_cfg.get("system") or {}
    if len(systems) != 1:
        raise ValueError("Analysis currently supports single-component systems only.")
    name = next(iter(systems))
    molecule_count = (systems[name] or {}).get("nmol", component_cfg.get("defaults", {}).get("nmol", 1))
    if int(molecule_count) != 1:
        raise ValueError("Rg analysis currently supports a single chain (nmol=1).")
    top = run_dir / "top.pdb"
    if not top.is_file():
        alternatives = [p for p in run_dir.glob("*.pdb") if "checkpoint" not in p.name.lower()]
        top = alternatives[0] if alternatives else top
    dcd = run_dir / f"{cfg.get('sysname', name)}.dcd"
    if not dcd.is_file():
        dcds = [p for p in run_dir.glob("*.dcd") if not p.name.startswith("equilibration")]
        if len(dcds) == 1:
            dcd = dcds[0]
    fasta = run_dir / "input" / "idp.fasta"
    fasta_setting = (systems[name] or {}).get("ffasta", component_cfg.get("defaults", {}).get("ffasta", "input/idp.fasta"))
    candidate = Path(str(fasta_setting))
    if not candidate.is_absolute():
        candidate = run_dir / candidate
    if candidate.is_file():
        fasta = candidate
    for label, path in (("topology", top), ("trajectory", dcd), ("FASTA", fasta)):
        if not path.is_file():
            raise FileNotFoundError(f"Missing {label}: {path}")
    return cfg, name, top, dcd, fasta


def analyze_run(run_dir: Path, stride: int = 1,
                theta_ref_nm: float = THETA_REF_NM,
                theta_ref_length: int = THETA_REF_LENGTH,
                theta_exponent: float = THETA_EXPONENT,
                out_dir: Path | None = None) -> dict:
    """Analyze a completed, single-chain trajectory; output reproducible artifacts."""
    if stride < 1:
        raise ValueError("stride must be at least 1")
    import MDAnalysis as mda
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    run_dir = Path(run_dir).resolve()
    cfg, name, top, dcd, fasta = locate_files(run_dir)
    seq = "".join(line.strip() for line in fasta.read_text(encoding="utf-8").splitlines()
                  if line.strip() and not line.startswith(">"))
    if not seq:
        raise ValueError("FASTA is empty.")
    universe = mda.Universe(str(top), str(dcd))
    if len(universe.atoms) != len(seq):
        raise ValueError(
            f"Topology has {len(universe.atoms)} beads but FASTA has {len(seq)} residues. "
            "Check single-chain setup."
        )
    try:
        masses = np.asarray(universe.atoms.masses, dtype=float)
    except (AttributeError, Exception):
        masses = np.ones(len(seq), dtype=float)
    if not np.isfinite(masses).all() or (masses <= 0).any():
        masses = np.ones(len(seq), dtype=float)
    masses /= masses.sum()

    rg = []
    for ts in universe.trajectory[::stride]:
        xyz = np.asarray(universe.atoms.positions, dtype=float) / 10  # Angstrom to nm
        center = np.sum(xyz * masses[:, None], axis=0)
        rg.append(float(np.sqrt(np.sum(masses * np.sum((xyz-center)**2, axis=1)))))
    rg = np.asarray(rg, dtype=float)

    # OpenMM uses a 0.01 ps integration step in the pinned CALVADOS version.
    sample_dt = float(cfg["wfreq"]) * TIMESTEP_PS / 1000 * stride
    threshold = theta_rg(len(seq), theta_ref_nm, theta_ref_length, theta_exponent)
    values = summarize_rg(rg, sample_dt, threshold)
    values.update({
        "name": name,
        "temperature_K": float(cfg["temp"]),
        "aa_length": len(seq),
        "sequence": seq,
        "stride": stride,
        "topology_file": str(top),
        "trajectory_file": str(dcd),
    })
    out_dir = Path(out_dir) if out_dir else run_dir / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = pd.DataFrame({
        "frame": np.arange(len(rg)) * stride + 1,
        "time_ns": (np.arange(len(rg)) + 1) * sample_dt,
        "rg_nm": rg,
        "collapsed": rg < threshold,
        "threshold_nm": threshold,
        "id": name,
        "temp": float(cfg["temp"]),
        "stride": stride,
        "frame_dt_ns": sample_dt / stride,
    })
    samples.to_csv(out_dir / "all_rg_values.csv", index=False)
    pd.DataFrame([values]).to_csv(out_dir / "summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(samples["time_ns"], rg, lw=1, color="#3869A6")
    ax.axhline(threshold, ls="--", color="#C55F43", label="Rg theta")
    ax.set(xlabel="Time (ns)", ylabel="Rg (nm)", title=f"{name} — Rg trace")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "rg_time.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3.8))
    ax.hist(rg, bins=min(40, max(5, int(np.sqrt(len(rg))))),
            color="#527B9A", alpha=.85, density=True)
    ax.axvline(threshold, ls="--", color="#C55F43", label="Rg theta")
    ax.set(xlabel="Rg (nm)", ylabel="Probability density", title="Rg distribution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "rg_distribution.png", dpi=180)
    plt.close(fig)
    methods = {
        "theta_definition": "Rg_theta(N) = sqrt(2*l_p_star*b*(N-1)/6); default l_p_star=0.40 nm, b=0.38 nm. Optional theta_ref_nm rescales the result.",
        "theta_persistence_length_nm": THETA_PERSISTENCE_LENGTH_NM,
        "theta_bond_length_nm": THETA_BOND_LENGTH_NM,
        "theta_ref_nm": theta_ref_nm,
        "theta_ref_length": theta_ref_length,
        "theta_exponent": theta_exponent,
        "collapsed_definition": "Rg < Rg_theta (no hysteresis)",
        "rate_definition": "number of observed transitions divided by corresponding state time (ns)",
        "dwell_definition": "first and last state segments excluded as censored",
        "mass_weighted": True,
        "coordinates": "MDAnalysis Angstrom converted to nm",
        "pbc_warning": "Coordinates assumed contiguous; wrapped chains may overestimate Rg",
        "time_step_ps": TIMESTEP_PS,
        "stride": stride,
        "note": "Short simulations or sparse transitions produce unreliable kinetic estimates.",
    }
    (out_dir / "methods.json").write_text(json.dumps(methods, indent=2), encoding="utf-8")
    return values


def main():
    parser = argparse.ArgumentParser(description="Analyze a local CALVADOS trajectory.")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--theta-ref-nm", type=float, default=THETA_REF_NM)
    args = parser.parse_args()
    print(json.dumps(analyze_run(args.run_dir, stride=args.stride,
                                 theta_ref_nm=args.theta_ref_nm), indent=2))


if __name__ == "__main__":
    main()
