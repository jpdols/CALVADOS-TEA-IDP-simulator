"""Static portability checks for Windows launcher assets (CI runs on Linux)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_portable_launcher_files_are_present():
    expected = (
        "windows/install_elp_studio.cmd",
        "windows/install_desktop_shortcut.ps1",
        "windows/start_elp_studio.vbs",
        "windows/start_elp_studio.ps1",
        "windows/stop_elp_studio.cmd",
        "windows/stop_elp_studio.ps1",
        "windows/create_icon.ps1",
    )
    for filename in expected:
        assert (ROOT / filename).is_file(), filename


def test_launcher_uses_checkout_directory_and_local_config():
    installer = (ROOT / "windows/install_desktop_shortcut.ps1").read_text(encoding="utf-8")
    launcher = (ROOT / "windows/start_elp_studio.ps1").read_text(encoding="utf-8")
    assert '$PSScriptRoot' in installer
    assert '$PSScriptRoot' in launcher
    assert "CONDA_PREFIX" in installer
    assert "python.exe" in installer
    assert ".elp_studio_launcher.json" in installer
    assert ".elp_studio_launcher.json" in launcher
    assert '"-m", "streamlit", "run", "app.py"' in launcher
    assert "--server.address" in launcher
    assert "127.0.0.1" in launcher
    for fixed_path in ("E:\\Master thesis", "E:\\conda_envs", "C:\\Users\\joep"):
        assert fixed_path not in installer
        assert fixed_path not in launcher


def test_runtime_artifacts_are_gitignored():
    ignores = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".elp_studio_launcher.json" in ignores
    assert ".elp_studio_runtime/" in ignores
    assert "assets/elp_studio.ico" in ignores
