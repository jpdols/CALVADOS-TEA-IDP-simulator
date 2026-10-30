"""Launch the generated CALVADOS run.py with a Windows checkpoint workaround.

Keeps exactly the CLI arguments produced by the pinned CALVADOS cfg.Config;
the generated simulation source and physics remain unchanged.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

from .checkpoint_compat import install_checkpoint_compat


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m calvados_library_builder.calvados_entrypoint RUN_PY [CALVADOS_ARGS]")
    run_script = Path(sys.argv[1]).resolve()
    if not run_script.is_file():
        raise FileNotFoundError(run_script)
    if install_checkpoint_compat():
        print(
            "Windows checkpoint compatibility enabled: writing restart files "
            "through OpenMM file handles, preserving .previous backup.",
            flush=True,
        )
    # The generated run.py uses argparse. Preserve the exact argument order
    # it expects, without changing any preparation or CALVADOS API call.
    sys.argv = [str(run_script), *sys.argv[2:]]
    runpy.run_path(str(run_script), run_name="__main__")


if __name__ == "__main__":
    main()
