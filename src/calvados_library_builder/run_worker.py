"""Run a prepared CALVADOS script and persist its actual exit code.

The wrapper persists a completion marker independent of Streamlit reruns.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m calvados_library_builder.run_worker RUN_PY EXIT_FILE")
    script = Path(sys.argv[1]).resolve()
    exit_file = Path(sys.argv[2]).resolve()
    try:
        result = subprocess.run([sys.executable, str(script)], cwd=str(script.parent), check=False)
        code = result.returncode
    except Exception as error:
        print(f"Unable to launch simulation: {error}", file=sys.stderr)
        code = 1
    exit_file.write_text(f"{code}\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
