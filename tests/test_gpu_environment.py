"""Regression guards: Windows install must preserve the proven CUDA 11.8 stack."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_reference_environment_matches_working_calvados():
    e = (ROOT / "environment.yml").read_text(encoding="utf-8")
    assert "name: calvados-tea-idp-simulator" in e
    assert "python=3.10" in e
    assert "openmm=8.2.0" in e
    assert "cudatoolkit=11.8.0" in e
    assert "cuda-version=12.8" not in e
    assert "  - pip:" not in e


def test_cloning_script_preserves_existing_gpu_engine():
    s = (ROOT / "windows/install_from_working_env.cmd").read_text(encoding="utf-8")
    p = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '--clone "%SOURCE%"' in s
    assert 'pip install --no-deps --no-build-isolation -e .' in s
    assert "python -m openmm.testInstallation" in s
    assert "calvados==0.8.0" in p
    assert '"openmm[cuda12]' not in p
