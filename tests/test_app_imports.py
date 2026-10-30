"""Catch missing app imports and truncated source files before launching Streamlit."""
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "calvados_library_builder"


def test_app_local_package_imports_are_defined():
    app = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    for node in ast.walk(app):
        if not isinstance(node, ast.ImportFrom):
            continue
        if not node.module or not node.module.startswith("calvados_library_builder."):
            continue
        module_name = node.module.rsplit(".", 1)[-1]
        module_path = PACKAGE / f"{module_name}.py"
        module_tree = ast.parse(module_path.read_text(encoding="utf-8"))
        defined = {
            n.name for n in module_tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        defined.update(
            target.id
            for n in module_tree.body
            if isinstance(n, ast.Assign)
            for target in n.targets
            if isinstance(target, ast.Name)
        )
        for alias in node.names:
            assert alias.name in defined, (
                f"app.py imports {alias.name} but {module_path} does not define it"
            )


def test_all_package_python_files_parse():
    for file in PACKAGE.glob("*.py"):
        ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
