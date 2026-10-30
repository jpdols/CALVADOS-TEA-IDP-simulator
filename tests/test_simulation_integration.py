"""Fast integration tests of preparation without requiring a GPU or CALVADOS install."""
from __future__ import annotations

import sys
import types

import pytest

from calvados_library_builder.config import SimulationConfig, validate_config
from calvados_library_builder.prepare import prepare_simulation


def test_temperature_requires_exact_existing_table(tmp_path):
    c = SimulationConfig("test", "VPGVG", temperature=370.5)
    with pytest.raises(ValueError, match="whole-number"):
        c.resolve_residue_file()


def test_reject_unsafe_simulation_name(tmp_path):
    file = tmp_path / "params.csv"
    file.write_text("one,lambdas\nV,0.5\n")
    c = SimulationConfig("../escape", "VPGVG", residue_file=file)
    with pytest.raises(ValueError, match="Simulation name"):
        validate_config(c)


def test_prepare_files_and_prevent_overwrite(monkeypatch, tmp_path):
    """Use CALVADOS API doubles to exercise our preparation logic without OpenMM."""
    residue = tmp_path / "residues.csv"
    residue.write_text("one,lambdas\nV,0.5\n")
    calvados_module = types.ModuleType("calvados")
    cfg_module = types.ModuleType("calvados.cfg")

    class FakeConfig:
        def __init__(self, **kwargs):
            self.settings = kwargs
        def write(self, path, name):
            (path / name).write_text(repr(self.settings))
            (path / "run.py").write_text("print('test')\n")

    class FakeComponents:
        def __init__(self, **kwargs):
            self.settings = kwargs
        def add(self, name):
            self.name = name
        def write(self, path, name):
            (path / name).write_text(repr(self.settings))

    cfg_module.Config = FakeConfig
    cfg_module.Components = FakeComponents
    monkeypatch.setitem(sys.modules, "calvados", calvados_module)
    monkeypatch.setitem(sys.modules, "calvados.cfg", cfg_module)

    config = SimulationConfig(
        name="test_vpgvg", sequence="VPGVG" * 2,
        temperature=370, platform="CPU",
        n_frames=10, save_every=100, seed=23,
        residue_file=residue, output_dir=tmp_path / "runs",
    )
    run_dir = prepare_simulation(config)
    assert (run_dir / "input" / "idp.fasta").read_text() == (
        ">test_vpgvg\nVPGVGVPGVG\n"
    )
    assert (run_dir / "input" / "residues.csv").exists()
    assert (run_dir / "run.py").exists()
    assert "random_number_seed': 23" in (run_dir / "config.yaml").read_text()
    assert "steps': 1000" in (run_dir / "config.yaml").read_text()
    assert "input/idp.fasta" in (run_dir / "components.yaml").read_text()
    with pytest.raises(FileExistsError, match="already contains"):
        prepare_simulation(config)
