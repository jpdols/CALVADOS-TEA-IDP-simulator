"""Independent replicate preparation plans and reproducible burn-in boundaries."""
from __future__ import annotations

import json

import pytest

from calvados_library_builder.analysis import discard_initial_frames, summarize_rg
from calvados_library_builder.designs import Candidate
from calvados_library_builder.replicates import (
    build_run_plan, validate_run_plan, write_replicate_info, read_replicate_info,
    experiment_from_path,
)


def test_triplicate_plans_distinct_runs_and_seeds(tmp_path):
    candidates = [
        Candidate("ELP_A", "VPGVG" * 10, "simple"),
        Candidate("ELP_B", "IPAVG" * 10, "simple"),
    ]
    runs = build_run_plan(candidates, tmp_path / "experiment", triplicate=True, first_seed=23)
    assert len(runs) == 6
    assert len({str(r.run_dir) for r in runs}) == 6
    assert [r.seed for r in runs] == [23, 24, 25, 26, 27, 28]
    assert [r.replicate for r in runs] == [1, 2, 3, 1, 2, 3]
    assert runs[0].run_dir == (tmp_path / "experiment" / "ELP_A" / "ELP_A__rep01").resolve()
    assert runs[1].simulation_name == "ELP_A__rep02"
    assert runs[0].sequence == runs[1].sequence == runs[2].sequence


def test_legacy_single_run_layout_unchanged(tmp_path):
    design = Candidate("ELP_A", "VPGVG", "simple")
    plan = build_run_plan([design], tmp_path / "experiment", first_seed=7)
    assert plan[0].run_dir == (tmp_path / "experiment" / "ELP_A").resolve()
    assert plan[0].simulation_name == "ELP_A"
    assert plan[0].replicate == 1


def test_refuse_overwriting_prepared_replicate(tmp_path):
    run = build_run_plan(
        [Candidate("ELP_A", "VPGVG", "simple")],
        tmp_path / "exp", triplicate=True,
    )[0]
    run.run_dir.mkdir(parents=True)
    (run.run_dir / "config.yaml").write_text("steps: 100\n")
    with pytest.raises(FileExistsError, match="already contains"):
        validate_run_plan([run])


def test_metadata_roundtrip(tmp_path):
    plan = build_run_plan(
        [Candidate("ELP_A", "VPGVG", "simple")],
        tmp_path / "exp", triplicate=True, first_seed=11
    )[1]
    plan.run_dir.mkdir(parents=True)
    write_replicate_info(plan, "exp")
    metadata = read_replicate_info(plan.run_dir)
    assert metadata["replicate"] == 2
    assert metadata["sequence_name"] == "ELP_A"
    assert metadata["random_seed"] == 12
    assert experiment_from_path(plan.run_dir, tmp_path) == "exp"


def test_discard_first_tenth_before_striding():
    assert discard_initial_frames(50, 0.1) == 5
    assert discard_initial_frames(99, 0.1) == 9
    assert discard_initial_frames(9, 0.1) == 0
    assert discard_initial_frames(50, 0) == 0
    with pytest.raises(ValueError):
        discard_initial_frames(10, 1.0)

    # First ten values are strongly expanded during equilibration.
    rg = [8.0]*10 + [3.0]*90
    trim = discard_initial_frames(len(rg), .1)
    untrimmed = summarize_rg(rg, .01, 4.6)
    trimmed = summarize_rg(rg[trim:], .01, 4.6)
    assert untrimmed["fraction_collapsed"] == pytest.approx(.9)
    assert trimmed["fraction_collapsed"] == pytest.approx(1.0)
    assert trimmed["mean_rg_nm"] == pytest.approx(3.0)
    assert trimmed["n_collapse_transitions"] == 0


def test_replicate_summary_averages_independent_runs():
    import pandas as pd
    from calvados_library_builder.replicate_summary import summarize_replicates
    data = pd.DataFrame([
        {"name":"ELP_A__rep01","sequence_name":"ELP_A","temperature_K":370.0,
         "fraction_collapsed":0.2,"mean_rg_nm":3.0,"k_collapse_per_ns":1.0},
        {"name":"ELP_A__rep02","sequence_name":"ELP_A","temperature_K":370.0,
         "fraction_collapsed":0.4,"mean_rg_nm":4.0,"k_collapse_per_ns":3.0},
        {"name":"ELP_A__rep03","sequence_name":"ELP_A","temperature_K":370.0,
         "fraction_collapsed":0.6,"mean_rg_nm":5.0,"k_collapse_per_ns":5.0},
    ])
    overview = summarize_replicates(data)
    assert len(overview) == 1
    assert overview.iloc[0]["n_replicates"] == 3
    assert overview.iloc[0]["fraction_collapsed_mean"] == pytest.approx(0.4)
    assert overview.iloc[0]["mean_rg_nm_mean"] == pytest.approx(4.0)
    assert overview.iloc[0]["mean_rg_nm_sd"] == pytest.approx(1.0)


def test_triplicate_preflight_rejects_legacy_parent(tmp_path):
    candidate = Candidate("ELP_A","VPGVG","simple")
    planned = build_run_plan([candidate],tmp_path/"exp",triplicate=True)
    parent = tmp_path/"exp"/"ELP_A"
    parent.mkdir(parents=True)
    (parent/"config.yaml").write_text("steps: 100\n")
    with pytest.raises(FileExistsError,match="existing single-run"):
        validate_run_plan(planned)
