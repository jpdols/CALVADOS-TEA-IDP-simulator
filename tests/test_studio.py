"""Fast no-GPU checks for designer, Rg definitions, and generated run paths."""
from pathlib import Path

import numpy as np
import pytest
import yaml

from calvados_library_builder.designs import make_library, simple_elp, validate_sequence
from calvados_library_builder.analysis import theta_rg, summarize_rg
from calvados_library_builder.preflight import inspect_run


def test_simple_elp_and_whitespace():
    assert simple_elp("x", "VPGVG", 3).sequence == "VPGVG" * 3
    assert validate_sequence("VPGVG\n IPAVG") == "VPGVGIPAVG"


def test_library_keeps_composition_and_seed():
    a = make_library(
        "screen", "VPGVG", "IPAVG", 20, [.25, .5],
        ["alternating", "diblock", "central", "shuffled"], 7,
    )
    b = make_library(
        "screen", "VPGVG", "IPAVG", 20, [.25, .5],
        ["alternating", "diblock", "central", "shuffled"], 7,
    )
    assert a == b
    assert len(a) == 8
    for design in a:
        nb = int(design.name.split("_B")[1][:3])
        assert design.sequence.count("IPAVG") == nb
        assert design.sequence.count("VPGVG") == 20 - nb


def test_rg_theta_reference_and_rates():
    assert theta_rg(420) == pytest.approx((2 * 0.40 * 0.38 * 419 / 6) ** 0.5)
    assert theta_rg(420) == pytest.approx(4.60753, abs=0.001)
    # expanded, expanded, compact, compact, expanded; one flip each way
    result = summarize_rg([5, 5, 3, 3, 5], 0.01, 4.0)
    assert result["fraction_collapsed"] == pytest.approx(.4)
    assert result["mean_rg_collapsed_nm"] == 3
    assert result["mean_rg_expanded_nm"] == 5
    assert result["n_collapse_transitions"] == 1
    assert result["n_escape_transitions"] == 1
    assert result["k_collapse_per_ns"] == pytest.approx(1 / .03)
    assert result["k_escape_per_ns"] == pytest.approx(1 / .02)
    assert result["mean_collapsed_dwell_ns"] == pytest.approx(.02)
    assert np.isnan(result["mean_expanded_dwell_ns"])  # both expanded segments censored


def test_preflight_detects_missing_and_accepts_complete(tmp_path):
    assert not inspect_run(tmp_path)["ok"]
    (tmp_path / "input").mkdir()
    (tmp_path / "input" / "idp.fasta").write_text(">x\nVPGVG\n")
    (tmp_path / "input" / "residues.csv").write_text("one,lambdas\nV,0.5\n")
    (tmp_path / "run.py").write_text("pass\n")
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(
        {"steps": 1000, "platform": "CPU", "sysname": "x"}
    ))
    (tmp_path / "components.yaml").write_text(yaml.safe_dump({
        "defaults": {"ffasta": "input/idp.fasta", "fresidues": "input/residues.csv"},
        "system": {"x": {}}
    }))
    report = inspect_run(tmp_path)
    assert report["ok"]
    assert "--path" in report["command_display"]
    assert "--config" in report["command_display"]
    assert "--components" in report["command_display"]
    (tmp_path / "input" / "idp.fasta").unlink()
    assert not inspect_run(tmp_path)["ok"]
