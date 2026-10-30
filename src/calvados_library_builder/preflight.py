"""Preflight check for generated CALVADOS input and exact run invocation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


def inspect_run(path: Path) -> dict:
    path = Path(path).resolve()
    config_file = path / "config.yaml"
    comp_file = path / "components.yaml"
    runner = path / "run.py"
    errors = []
    for f in (config_file, comp_file, runner):
        if not f.is_file():
            errors.append(f"Missing required file: {f.name}")
    if errors:
        return {"ok": False, "errors": errors, "run_dir": str(path)}
    try:
        config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        comps = yaml.safe_load(comp_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "errors": [f"Invalid YAML: {exc}"], "run_dir": str(path)}
    systems = comps.get("system", {})
    defaults = comps.get("defaults", {})
    for name, override in systems.items():
        component = {**defaults, **(override or {})}
        for field in ("ffasta", "fresidues"):
            value = component.get(field)
            if not value:
                errors.append(f"Component {name}: {field} is missing")
                continue
            file = Path(str(value))
            if not file.is_absolute():
                file = path / file
            if not file.is_file():
                errors.append(f"Component {name}: {field} does not exist: {file}")
    if not systems:
        errors.append("components.yaml has no system entries")
    if config.get("steps") is None:
        errors.append("config.yaml does not define steps")
    if config.get("platform") not in ("CPU", "CUDA"):
        errors.append("CALVADOS accepts CPU or CUDA as platform")
    command = [
        sys.executable, str(runner), "--path", str(path),
        "--config", "config.yaml", "--components", "components.yaml",
    ]
    return {
        "ok": not errors, "errors": errors, "run_dir": str(path),
        "platform": config.get("platform"), "steps": config.get("steps"),
        "command": command,
        "command_display": " ".join(f'"{arg}"' if " " in arg else arg for arg in command),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    result = inspect_run(args.run_dir)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
