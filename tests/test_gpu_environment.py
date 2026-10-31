"""Keep Conda-managed OpenMM/CUDA separate from pip CUDA extras."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_gpu_conda_environment_pins_compatible_cuda():
    environment = (ROOT / "environment.yml").read_text(encoding="utf-8")
    assert "python=3.11" in environment
    assert "openmm=8.2.0" in environment
    assert "cuda-version=12.8" in environment
    assert "cudatoolkit=11.8" not in environment.replace(
        "# The win-64 OpenMM 8.2 py311 build requires CUDA 12 (not cudatoolkit 11.8).", ""
    )
    assert "  - pip:" not in environment


def test_gpu_installer_prevents_pip_cuda_extra_installation():
    installer = (ROOT / "windows/finish_install.cmd").read_text(encoding="utf-8")
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "openmm==8.2.0" in project
    assert '"openmm[cuda12]' not in project
    assert "pip install --no-deps" in installer
    assert "getForces=True" in installer
    assert "df7d12a3428a0151a9c4683e1300e086d67d8fa5" in installer
