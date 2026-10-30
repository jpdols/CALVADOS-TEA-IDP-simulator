"""Aggregate independently analyzed replicate results per sequence/condition."""
from __future__ import annotations

import pandas as pd

REPLICATE_METRICS = (
    "fraction_collapsed",
    "mean_rg_nm",
    "mean_rg_collapsed_nm",
    "k_collapse_per_ns",
    "k_escape_per_ns",
)


def summarize_replicates(table: pd.DataFrame) -> pd.DataFrame:
    """Return per-sequence means and between-replicate SD; no frames are pooled.

    One row per sequence and temperature. SD is NaN for a single run. The mean
    of per-run state fractions is unweighted; users should compare runs of
    comparable length after equilibration removal.
    """
    if table.empty:
        return pd.DataFrame()
    source = table.copy()
    if "sequence_name" not in source:
        source["sequence_name"] = source["name"].astype(str).str.replace(
            r"__rep\d+$", "", regex=True,
        )
    if "temperature_K" not in source:
        source["temperature_K"] = float("nan")
    metrics = [key for key in REPLICATE_METRICS if key in source.columns]
    for key in metrics:
        source[key] = pd.to_numeric(source[key], errors="coerce")
    keys = ["sequence_name", "temperature_K"]
    if "experiment" in source.columns:
        keys.insert(0, "experiment")
    grouped = source.groupby(keys, dropna=False, sort=True)
    counts = grouped.size().rename("n_replicates")
    result = counts.to_frame()
    for metric in metrics:
        result[f"{metric}_mean"] = grouped[metric].mean()
        result[f"{metric}_sd"] = grouped[metric].std(ddof=1)
    return result.reset_index()
