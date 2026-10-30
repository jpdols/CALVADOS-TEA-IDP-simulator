"""Plan reproducible single or triplicate CALVADOS simulation folders.

Triplicate layout:
  runs/<experiment>/<sequence>/<sequence>__rep01/
  runs/<experiment>/<sequence>/<sequence>__rep02/
  runs/<experiment>/<sequence>/<sequence>__rep03/

Each replicate has independent config, seed, trajectory, logs and analysis.
Existing single-run layout (runs/<experiment>/<sequence>/) is unchanged.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .designs import Candidate

MAX_RANDOM_SEED = 2147483646
RUN_INFO_FILENAME = "replicate_info.json"
VALID_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")


@dataclass(frozen=True)
class PlannedRun:
    sequence_name: str
    simulation_name: str
    sequence: str
    batch_dir: Path
    run_dir: Path
    replicate: int
    replicate_count: int
    seed: int


def build_run_plan(
    candidates: Iterable[Candidate],
    experiment_dir: Path,
    *,
    triplicate: bool = False,
    first_seed: int = 1,
) -> list[PlannedRun]:
    """Generate all destinations and distinct seeds before writing files.

    Naming is deterministic, and collisions are rejected rather than
    overwriting any files, prior queue entries or previously analyzed results.
    """
    designs = list(candidates)
    if not designs:
        raise ValueError("No ELP sequences selected.")
    n_replicates = 3 if triplicate else 1
    if isinstance(first_seed, bool) or not isinstance(first_seed, int) or first_seed < 0:
        raise ValueError("Starting random seed must be a nonnegative integer.")
    if first_seed + len(designs) * n_replicates - 1 > MAX_RANDOM_SEED:
        raise ValueError("Random seed range exceeds the supported limit.")

    experiment_dir = Path(experiment_dir).resolve()
    planned: list[PlannedRun] = []
    used_names: set[str] = set()
    used_paths: set[str] = set()
    for i, candidate in enumerate(designs):
        name = candidate.name
        if not VALID_NAME.fullmatch(name) or name.endswith("."):
            raise ValueError(f"Unsafe sequence name: {name!r}.")
        if name.casefold() in used_names:
            raise ValueError(f"Duplicate sequence name: {name}.")
        used_names.add(name.casefold())
        for index in range(1, n_replicates + 1):
            sim_name = f"{name}__rep{index:02d}" if triplicate else name
            # Keep the original single-run layout unchanged.
            parent = experiment_dir / name if triplicate else experiment_dir
            run_dir = parent / sim_name
            key = str(run_dir).casefold()
            if key in used_paths:
                raise ValueError(f"Duplicate destination: {run_dir}")
            used_paths.add(key)
            planned.append(PlannedRun(
                sequence_name=name,
                simulation_name=sim_name,
                sequence=candidate.sequence,
                batch_dir=parent,
                run_dir=run_dir,
                replicate=index,
                replicate_count=n_replicates,
                seed=first_seed + i * n_replicates + (index - 1),
            ))
    return planned


def validate_run_plan(planned: list[PlannedRun], existing_items: Iterable = ()) -> None:
    """Fail early if a new run would overwrite an existing folder or queue item."""
    known_names = {str(item.name).casefold() for item in existing_items}
    known_paths = {str(Path(item.run_dir).resolve()).casefold() for item in existing_items}
    for item in planned:
        if item.simulation_name.casefold() in known_names:
            raise FileExistsError(f"Simulation already exists in queue: {item.simulation_name}")
        if str(item.run_dir).casefold() in known_paths:
            raise FileExistsError(f"Run folder is already queued: {item.run_dir}")
        if item.replicate_count > 1 and (item.batch_dir / "config.yaml").exists():
            raise FileExistsError(
                f"Cannot nest triplicate outputs inside an existing single-run directory: "
                f"{item.batch_dir}. Choose a new experiment name."
            )
        if item.run_dir.exists() and any(item.run_dir.iterdir()):
            raise FileExistsError(f"Run folder already contains files: {item.run_dir}")


def write_replicate_info(plan: PlannedRun, experiment_name: str) -> Path:
    """Write metadata beside CALVADOS outputs for later analysis grouping."""
    if not plan.run_dir.is_dir():
        raise FileNotFoundError(f"Prepared run directory is missing: {plan.run_dir}")
    dest = plan.run_dir / RUN_INFO_FILENAME
    if dest.exists():
        raise FileExistsError(f"Existing replicate metadata will not be overwritten: {dest}")
    info = {
        "schema_version": 1,
        "experiment": experiment_name,
        "sequence_name": plan.sequence_name,
        "simulation_name": plan.simulation_name,
        "replicate": plan.replicate,
        "replicate_count": plan.replicate_count,
        "random_seed": plan.seed,
    }
    dest.write_text(json.dumps(info, indent=2), encoding="utf-8")
    return dest


def read_replicate_info(run_dir: Path) -> dict:
    """Return saved replicate metadata, or an empty object for legacy runs."""
    dest = Path(run_dir) / RUN_INFO_FILENAME
    if not dest.exists():
        return {}
    info = json.loads(dest.read_text(encoding="utf-8"))
    if not isinstance(info, dict) or info.get("schema_version") != 1:
        raise ValueError(f"Invalid replicate metadata: {dest}")
    return info


def experiment_from_path(run_dir: Path, runs_root: Path) -> str:
    """Resolve batch name consistently for flat and nested layouts."""
    relative = Path(run_dir).resolve().relative_to(Path(runs_root).resolve())
    return relative.parts[0] if len(relative.parts) > 1 else "(standalone)"
