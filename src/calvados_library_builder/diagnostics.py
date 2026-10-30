"""Inspect local CALVADOS/OpenMM install and supported execution platforms."""
from __future__ import annotations
import sys

def available_platforms() -> dict[str, str]:
    try:
        import openmm
        found = {}
        for i in range(openmm.Platform.getNumPlatforms()):
            p = openmm.Platform.getPlatform(i)
            found[p.getName()] = "installed"
        return found
    except Exception as e:
        return {"error": str(e)}

def main() -> None:
    print("Python:", sys.version.split()[0])
    try:
        import importlib.metadata as meta
        for package in ("calvados", "openmm", "MDAnalysis", "mdtraj", "streamlit"):
            try:
                print(f"{package}: {meta.version(package)}")
            except meta.PackageNotFoundError:
                print(f"{package}: not installed")
    except ImportError:
        pass
    print("OpenMM platforms:", available_platforms())
    print("CALVADOS run configuration supports: CPU, CUDA.")
    print("CUDA availability requires compatible NVIDIA drivers and runtime.")

if __name__ == "__main__":
    main()
