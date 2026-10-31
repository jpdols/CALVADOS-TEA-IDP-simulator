#!/usr/bin/env python3
"""Portable ELP Studio installer: NVIDIA CUDA first, safe CPU fallback.

Run from the cloned repository:
    python install.py

Requires Conda/Miniforge and Git. Creates a separate Conda environment named
calvados-tea-idp-simulator; never clones or modifies a user's other environments.

CALVADOS 0.8.0 is pinned to a public upstream Git revision. The exact
OpenMM 8.2 / cudatoolkit 11.8 combination was validated on Windows with
Python 3.10, but GPU compatibility on other hardware is determined by an
actual force calculation, not by merely detecting a CUDA platform name.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_NAME = "calvados-tea-idp-simulator"
CALVADOS_REVISION = "75711acbf87cc28e00959b8fb38d5132f66709e4"
CALVADOS_URL = (
    "git+https://github.com/KULL-Centre/CALVADOS.git@" + CALVADOS_REVISION
)
PIP_CONSTRAINTS = ROOT / "install_constraints.txt"

# Tests the actual OpenMM CUDA/CPU force evaluation. A registered CUDA plugin
# alone is insufficient (e.g. CUDA_ERROR_UNSUPPORTED_PTX_VERSION).
OPENMM_FORCE_PROBE = """
import sys
import numpy as np
import openmm
from openmm import unit
platform = openmm.Platform.getPlatformByName(sys.argv[1])
system = openmm.System()
system.addParticle(1.0)
system.addParticle(1.0)
bond = openmm.HarmonicBondForce()
bond.addBond(0, 1, 0.2, 100.0)
system.addForce(bond)
integrator = openmm.VerletIntegrator(0.001)
context = openmm.Context(system, integrator, platform)
context.setPositions([[0, 0, 0], [0.3, 0, 0]])
forces = context.getState(getForces=True).getForces(
    asNumpy=True
).value_in_unit(unit.kilojoule_per_mole / unit.nanometer)
assert np.isfinite(forces).all(), 'Nonfinite forces'
print(platform.getName(), 'computed finite forces with OpenMM', openmm.version.full_version)
"""

VERSION_PROBE = """
import sys
from importlib import metadata
assert sys.version_info[:2] == (3, 10), sys.version
assert metadata.version('openmm') == '8.2.0'
assert metadata.version('calvados') == '0.8.0'
import calvados
from calvados.cfg import Config, Components
import MDAnalysis, mdtraj, streamlit, openpyxl, localcider
import calvados_library_builder.prepare
print('CALVADOS / ELP Studio imports verified')
"""


class SetupError(RuntimeError):
    """Actionable setup failure; does not imply other environments changed."""


def baseline_specs(file: Path = ROOT / "environment.yml") -> list[str]:
    """Read the simple Conda dependencies list without a PyYAML prerequisite."""
    specs: list[str] = []
    section = ""
    for raw in file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if raw == "dependencies:":
            section = "dependencies"
            continue
        if not raw.startswith(" ") and raw.endswith(":"):
            section = raw[:-1]
            continue
        if section == "dependencies" and raw.startswith("  - "):
            spec = raw[4:].strip().strip('"').strip("'")
            if not spec or spec == "pip:":
                raise SetupError("Invalid dependency entry in environment.yml")
            specs.append(spec)
    if not specs or not any(s.startswith("openmm=") for s in specs):
        raise SetupError("Cannot read the CPU baseline from environment.yml")
    if any(s.startswith(("cuda-version", "cudatoolkit", "cuda-")) for s in specs):
        raise SetupError("The CPU baseline must not require CUDA")
    return specs


def gpu_specs(specs: list[str]) -> list[str]:
    """The only extra runtime dependency on the CUDA-first attempt."""
    return [*specs, "cudatoolkit=11.8.0"]


def command(cmd: list[str], *, capture: bool = False, cwd: Path = ROOT):
    # shlex.join is missing in some older Conda base Python installations.
    if os.name == "nt":
        display = subprocess.list2cmdline([str(x) for x in cmd])
    else:
        display = " ".join(shlex.quote(str(x)) for x in cmd)
    print("+", display, flush=True)
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )


def conda_executable() -> str:
    executable = os.environ.get("CONDA_EXE") or shutil.which("conda")
    if not executable:
        raise SetupError(
            "Conda not found. Install Miniforge and run this command from "
            "Anaconda Prompt / a Conda-enabled terminal."
        )
    return executable


def all_environments(conda: str) -> list[Path]:
    result = command([conda, "env", "list", "--json"], capture=True)
    if result.returncode:
        raise SetupError("Unable to inspect Conda environments:\n" + result.stdout)
    try:
        return [Path(p) for p in json.loads(result.stdout)["envs"]]
    except (ValueError, KeyError) as exc:
        raise SetupError("Conda returned an invalid environment listing") from exc


def destination_exists(conda: str) -> bool:
    return any(
        p.name.casefold() == ENV_NAME.casefold() for p in all_environments(conda)
    )


def nvidia_detected() -> bool:
    """No CUDA toolkit required to check for a working NVIDIA driver."""
    executable = shutil.which("nvidia-smi")
    if not executable and os.name == "nt":
        for candidate in (
            Path(os.environ.get("WINDIR", "C:/Windows")) / "System32" / "nvidia-smi.exe",
            Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            / "NVIDIA Corporation" / "NVSMI" / "nvidia-smi.exe",
        ):
            if candidate.is_file():
                executable = str(candidate)
                break
    if not executable:
        return False
    try:
        result = subprocess.run(
            [executable, "-L"], capture_output=True, text=True, timeout=15
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and bool(
        re.search(r"\bGPU\s+\d+:", result.stdout)
    )


def create_environment(conda: str, specs: list[str]) -> bool:
    cmd = [
        conda, "create", "-y", "--override-channels", "-c", "conda-forge",
        "-n", ENV_NAME, *specs,
    ]
    return command(cmd).returncode == 0


def remove_new_environment(conda: str) -> None:
    """ONLY for an environment created by this invocation of install.py."""
    if destination_exists(conda):
        result = command([conda, "env", "remove", "-y", "-n", ENV_NAME])
        if result.returncode or destination_exists(conda):
            raise SetupError(
                "Could not clean up the newly created GPU environment. "
                "Check 'conda env list' before retrying; nothing else "
                "has been removed."
            )


def conda_python(conda: str, *args: str, capture: bool = False):
    # Some older Conda versions do not support --no-capture-output.
    # Use the portable 'conda run -n ... python' invocation instead.
    cmd = [conda, "run", "-n", ENV_NAME, "python", *args]
    return command(cmd, capture=capture)


def probe_platform(conda: str, platform: str) -> bool:
    result = conda_python(
        conda, "-c", OPENMM_FORCE_PROBE, platform, capture=True
    )
    if result.stdout:
        print(result.stdout.strip(), flush=True)
    return result.returncode == 0


def verify_existing(conda: str) -> bool:
    """Protect against overwriting a different, older environment."""
    result = conda_python(conda, "-c", VERSION_PROBE, capture=True)
    if result.stdout:
        print(result.stdout.strip(), flush=True)
    return result.returncode == 0


def install_app(conda: str) -> None:
    print("\nInstalling Streamlit and supporting Python packages...", flush=True)
    pip_base = ["-m", "pip", "install", "-c", str(PIP_CONSTRAINTS)]
    result = conda_python(
        conda, *pip_base, "streamlit==1.58.0", "openpyxl==3.1.5",
        "localcider==0.1.21",
    )
    if result.returncode:
        raise SetupError("Unable to install Streamlit or its dependencies.")

    # Do not allow pip to replace conda-forge's OpenMM/CUDA binary packages.
    print("\nInstalling public pinned CALVADOS 0.8.0 source...", flush=True)
    result = conda_python(
        conda, "-m", "pip", "install", "--no-deps", "--no-build-isolation",
        CALVADOS_URL,
    )
    if result.returncode:
        raise SetupError("Could not install CALVADOS from its pinned Git revision.")

    print("\nInstalling ELP Studio without changing OpenMM...", flush=True)
    result = conda_python(
        conda, "-m", "pip", "install", "--no-deps", "--no-build-isolation",
        "-e", ".",
    )
    if result.returncode:
        raise SetupError("Could not install ELP Studio in editable mode.")

    if not verify_existing(conda):
        raise SetupError("ELP Studio import/version verification failed.")

    print("\nRunning application unit tests...", flush=True)
    result = conda_python(conda, "-m", "pytest", "-q")
    if result.returncode:
        raise SetupError(
            "Unit tests failed. Inspect the tracebacks before running production MD."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--cpu", action="store_true", help="Skip GPU attempt")
    mode.add_argument("--gpu", action="store_true", help="Attempt GPU even without nvidia-smi")
    mode.add_argument("--update", action="store_true", help="Update app in existing compatible environment")
    mode.add_argument("--check", action="store_true", help="Check existing environment without changing it")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan; make no changes")
    args = parser.parse_args(argv)

    try:
        specs = baseline_specs()
        gpu_candidate = not args.cpu and (
            args.gpu or (sys.platform != "darwin" and nvidia_detected())
        )
        if args.dry_run:
            print("Environment:", ENV_NAME)
            print("GPU attempt:", gpu_candidate)
            print("Conda packages:", ", ".join(gpu_specs(specs) if gpu_candidate else specs))
            print("CPU fallback:", gpu_candidate)
            print("CALVADOS Git revision:", CALVADOS_REVISION)
            return 0

        conda = conda_executable()
        exists = destination_exists(conda)
        if args.check:
            if not exists:
                raise SetupError(f"Environment {ENV_NAME!r} does not exist.")
            if not verify_existing(conda):
                raise SetupError("Existing environment does not match expected CALVADOS 0.8 baseline.")
            backend = "CUDA" if probe_platform(conda, "CUDA") else "CPU"
            if not probe_platform(conda, "CPU"):
                raise SetupError("CPU force calculation failed.")
            print("Installation check PASSED. Working backend:", backend)
            return 0

        if exists and not args.update:
            raise SetupError(
                f"Environment {ENV_NAME!r} already exists. "
                "Run 'python install.py --check' to inspect it, "
                "or 'python install.py --update' if it is compatible. "
                "Never delete an existing environment without reviewing it."
            )
        if args.update and not exists:
            raise SetupError(f"Environment {ENV_NAME!r} does not exist; use python install.py")
        if exists and args.update and not verify_existing(conda):
            raise SetupError(
                "Existing environment has different versions. It was NOT modified. "
                "Inspect with 'conda list -n calvados-tea-idp-simulator'."
            )

        backend = "CPU"
        if not exists:
            if gpu_candidate:
                print("\nNVIDIA device detected: trying CUDA 11.8 + OpenMM 8.2...", flush=True)
                created = create_environment(conda, gpu_specs(specs))
                if created and probe_platform(conda, "CUDA"):
                    backend = "CUDA"
                    print("CUDA force calculation PASSED.", flush=True)
                else:
                    print("\nCUDA setup/force check failed; falling back to CPU.", flush=True)
                    remove_new_environment(conda)
            else:
                print("\nNo usable NVIDIA device detected; installing CPU version.", flush=True)

            if not destination_exists(conda):
                if not create_environment(conda, specs):
                    raise SetupError(
                        "CPU Conda environment could not be resolved. "
                        "Check the Conda solver output above."
                    )
            if not probe_platform(conda, "CPU"):
                raise SetupError("OpenMM CPU force calculation failed.")

        else:
            backend = "CUDA" if probe_platform(conda, "CUDA") else "CPU"
            if not probe_platform(conda, "CPU"):
                raise SetupError("Existing environment CPU force calculation failed.")

        install_app(conda)
        if backend == "CUDA" and not probe_platform(conda, "CUDA"):
            print("WARNING: CUDA no longer initializes; CPU remains available.")
            backend = "CPU"

        print("\n" + "=" * 60)
        print("ELP STUDIO INSTALLED SUCCESSFULLY")
        print("Environment:", ENV_NAME)
        print("Validated backend:", backend)
        print("Activate: conda activate", ENV_NAME)
        print("Launch:   python -m streamlit run app.py")
        print("Check:    python install.py --check")
        print("=" * 60)
        return 0
    except (SetupError, OSError) as exc:
        print("\nINSTALLATION ERROR:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
