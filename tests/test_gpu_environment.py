"""One-command installer: portable GPU attempt, verified CPU fallback."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_installer():
    spec = importlib.util.spec_from_file_location("elp_installer", ROOT / "install.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cpu_baseline_and_gpu_variant():
    installer = load_installer()
    specs = installer.baseline_specs()
    assert "python=3.10" in specs
    assert "openmm=8.2.0" in specs
    assert "cudatoolkit=11.8.0" not in specs
    assert "cudatoolkit=11.8.0" in installer.gpu_specs(specs)
    assert "cuda-version=12.8" not in specs


def test_upstream_is_pinned_and_path_independent():
    installer = load_installer()
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    script = (ROOT / "windows/install_from_working_env.cmd").read_text(
        encoding="utf-8"
    )
    assert "75711acbf87cc28e00959b8fb38d5132f66709e4" in installer.CALVADOS_URL
    assert "calvados==0.8.0" in project
    assert '"openmm[cuda12]' not in project
    assert 'pip", "install", "--no-deps"' in (ROOT / "install.py").read_text(
        encoding="utf-8"
    )
    assert "python install.py" in script
    assert "E:\\conda_envs" not in script
    assert "mep-calvados" not in script


def test_nvidia_detection_parses_nvidia_smi_output():
    installer = load_installer()
    class Done:
        returncode = 0
        stdout = "GPU 0: NVIDIA RTX 4090 (UUID: GPU-test)"

    with patch.object(installer.shutil, "which", return_value="nvidia-smi"), \
         patch.object(installer.subprocess, "run", return_value=Done()):
        assert installer.nvidia_detected()


def test_missing_nvidia_chooses_cpu_dry_run(capsys):
    installer = load_installer()
    with patch.object(installer, "nvidia_detected", return_value=False):
        assert installer.main(["--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "GPU attempt: False" in output


def test_gpu_force_failure_falls_back_to_cpu():
    installer = load_installer()
    called = {"create": [], "probe": [], "install": 0, "removed": 0}
    exists = iter([False, False, False])  # initial, remove, post-fallback
    def create(conda, specs):
        called["create"].append(tuple(specs))
        return True
    def probe(conda, platform):
        called["probe"].append(platform)
        return platform == "CPU"
    def remove(conda):
        called["removed"] += 1
    def app(conda):
        called["install"] += 1
    with patch.object(installer, "conda_executable", return_value="conda"), \
         patch.object(installer, "nvidia_detected", return_value=True), \
         patch.object(installer, "destination_exists", return_value=False), \
         patch.object(installer, "create_environment", side_effect=create), \
         patch.object(installer, "remove_new_environment", side_effect=remove), \
         patch.object(installer, "probe_platform", side_effect=probe), \
         patch.object(installer, "install_app", side_effect=app):
        assert installer.main([]) == 0
    assert len(called["create"]) == 2
    assert "cudatoolkit=11.8.0" in called["create"][0]
    assert "cudatoolkit=11.8.0" not in called["create"][1]
    assert called["removed"] == 1
    assert called["install"] == 1


def test_conda_run_works_without_newer_flags():
    installer = load_installer()
    with patch.object(installer, "command") as mocked:
        mocked.return_value.returncode = 0
        installer.conda_python("conda", "-V")
    args = mocked.call_args.args[0]
    assert args[:5] == ["conda", "run", "-n", installer.ENV_NAME, "python"]
    assert "--no-capture-output" not in args


def test_print_command_does_not_require_shlex_join(capsys):
    installer = load_installer()
    with patch.object(installer.subprocess, "run") as mocked:
        mocked.return_value.returncode = 0
        installer.command(["conda", "env", "list", "--json"])
    assert "conda" in capsys.readouterr().out
