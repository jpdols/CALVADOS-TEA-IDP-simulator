"""Validate embedded draggable-editor JavaScript before shipping the app."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from calvados_library_builder import motif_canvas


def test_canvas_structure_and_accessible_controls():
    assert "elp-bracket" in motif_canvas.CSS
    assert "elp-tools" in motif_canvas.CSS
    assert 'tool("+1"' in motif_canvas.JS
    assert 'tool("−1"' in motif_canvas.JS
    assert 'tool("⫽"' in motif_canvas.JS
    assert 'tool("×"' in motif_canvas.JS
    assert "setStateValue" in motif_canvas.JS
    assert "application/x-elp-run" in motif_canvas.JS


def test_javascript_module_syntax(tmp_path: Path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is not installed; manual browser smoke test required.")
    script = tmp_path / "motif_canvas.mjs"
    script.write_text(motif_canvas.JS, encoding="utf-8")
    result = subprocess.run(
        [node, "--check", str(script)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
