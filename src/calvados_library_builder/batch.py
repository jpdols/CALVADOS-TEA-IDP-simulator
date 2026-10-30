#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import time

from dataclasses import asdict, dataclass, field
from pathlib import Path

from .runner import (
    get_run_summary,
    load_run_state,
    process_exists,
    start_run,
)


# ============================================================
# Batch files
# ============================================================

BATCH_STATE_FILENAME = "batch_state.json"


# ============================================================
# Batch item
# ============================================================

@dataclass
class BatchItem:
    """
    One CALVADOS simulation inside a batch.
    """

    name: str
    run_dir: str

    expected_frames: int

    status: str = "queued"

    added_at: float = field(
        default_factory=time.time
    )

    started_at: float | None = None
    finished_at: float | None = None

    message: str = ""


# ============================================================
# Batch state
# ============================================================

@dataclass
class BatchState:
    """
    Collection of CALVADOS simulations that should
    be executed sequentially.
    """

    name: str
    batch_dir: str

    status: str = "building"

    created_at: float = field(
        default_factory=time.time
    )

    started_at: float | None = None
    finished_at: float | None = None

    current_index: int | None = None

    items: list[BatchItem] = field(
        default_factory=list
    )


# ============================================================
# Paths
# ============================================================

def get_batch_state_path(
    batch_dir: Path,
) -> Path:

    return (
        Path(batch_dir)
        / BATCH_STATE_FILENAME
    )


# ============================================================
# Save batch
# ============================================================

def save_batch(
    batch: BatchState,
) -> None:
    """
    Save the batch state to JSON.
    """

    batch_dir = Path(
        batch.batch_dir
    )

    batch_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    state_path = get_batch_state_path(
        batch_dir
    )

    state_path.write_text(
        json.dumps(
            asdict(batch),
            indent=2,
        ),
        encoding="utf-8",
    )


# ============================================================
# Load batch
# ============================================================

def load_batch(
    batch_dir: Path,
) -> BatchState:
    """
    Load a batch from disk.
    """

    batch_dir = Path(
        batch_dir
    ).resolve()

    state_path = get_batch_state_path(
        batch_dir
    )

    if not state_path.exists():

        raise FileNotFoundError(
            f"No batch state found in {batch_dir}"
        )

    data = json.loads(
        state_path.read_text(
            encoding="utf-8"
        )
    )

    items = [
        BatchItem(
            **item
        )
        for item in data.get(
            "items",
            []
        )
    ]

    return BatchState(
        name=data["name"],
        batch_dir=data["batch_dir"],
        status=data.get(
            "status",
            "building",
        ),
        created_at=data.get(
            "created_at",
            time.time(),
        ),
        started_at=data.get(
            "started_at"
        ),
        finished_at=data.get(
            "finished_at"
        ),
        current_index=data.get(
            "current_index"
        ),
        items=items,
    )


# ============================================================
# Create batch
# ============================================================

def create_batch(
    name: str,
    batch_dir: Path,
) -> BatchState:
    """
    Create a new empty simulation batch.
    """

    name = name.strip()

    if not name:

        raise ValueError(
            "Batch name cannot be empty."
        )

    batch_dir = Path(
        batch_dir
    ).resolve()

    batch_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    state_path = get_batch_state_path(
        batch_dir
    )

    if state_path.exists():

        raise FileExistsError(
            f"A batch already exists at {batch_dir}"
        )

    batch = BatchState(
        name=name,
        batch_dir=str(
            batch_dir
        ),
    )

    save_batch(
        batch
    )

    return batch


# ============================================================
# Add simulation
# ============================================================

def add_simulation(
    batch: BatchState,
    name: str,
    run_dir: Path,
    expected_frames: int,
) -> BatchState:
    """
    Add a prepared CALVADOS simulation to the queue.
    """

    name = name.strip()

    run_dir = Path(
        run_dir
    ).resolve()

    if not name:

        raise ValueError(
            "Simulation name cannot be empty."
        )

    if not run_dir.exists():

        raise FileNotFoundError(
            f"Simulation directory does not exist: "
            f"{run_dir}"
        )

    if expected_frames <= 0:

        raise ValueError(
            "Expected frames must be greater than zero."
        )

    existing_names = {
        item.name
        for item in batch.items
    }

    if name in existing_names:

        raise ValueError(
            f"Simulation '{name}' is already "
            f"in this batch."
        )

    item = BatchItem(
        name=name,
        run_dir=str(
            run_dir
        ),
        expected_frames=int(
            expected_frames
        ),
    )

    batch.items.append(
        item
    )

    save_batch(
        batch
    )

    return batch


# ============================================================
# Remove queued simulation
# ============================================================

def remove_simulation(
    batch: BatchState,
    name: str,
) -> BatchState:
    """
    Remove a simulation that has not started yet.
    """

    for index, item in enumerate(
        batch.items
    ):

        if item.name != name:

            continue

        if item.status == "running":

            raise RuntimeError(
                "Cannot remove a running simulation."
            )

        del batch.items[
            index
        ]

        save_batch(
            batch
        )

        return batch

    raise KeyError(
        f"Simulation '{name}' was not found."
    )


# ============================================================
# Find running item
# ============================================================

def get_running_index(
    batch: BatchState,
) -> int | None:
    """
    Return index of currently running simulation.
    """

    for index, item in enumerate(
        batch.items
    ):

        if item.status == "running":

            return index

    return None


# ============================================================
# Find next queued item
# ============================================================

def get_next_queued_index(
    batch: BatchState,
) -> int | None:
    """
    Return index of the next queued simulation.
    """

    for index, item in enumerate(
        batch.items
    ):

        if item.status == "queued":

            return index

    return None


# ============================================================
# Start one item
# ============================================================

def start_item(
    batch: BatchState,
    index: int,
) -> BatchState:
    """
    Start one simulation in the batch.
    """

    item = batch.items[
        index
    ]

    if item.status != "queued":

        raise RuntimeError(
            f"Simulation '{item.name}' is not queued."
        )

    state = start_run(
        run_dir=Path(
            item.run_dir
        ),
        expected_frames=(
            item.expected_frames
        ),
    )

    item.status = "running"
    item.started_at = (
        state.started_at
    )

    item.message = (
        "CALVADOS simulation running."
    )

    batch.current_index = (
        index
    )

    if batch.started_at is None:

        batch.started_at = (
            time.time()
        )

    batch.status = "running"

    save_batch(
        batch
    )

    return batch


# ============================================================
# Start batch
# ============================================================

def start_batch(
    batch: BatchState,
) -> BatchState:
    """
    Start the first queued simulation.

    Only one simulation is started at a time.
    """

    if not batch.items:

        raise RuntimeError(
            "Batch contains no simulations."
        )

    running_index = (
        get_running_index(
            batch
        )
    )

    if running_index is not None:

        raise RuntimeError(
            "A simulation in this batch "
            "is already running."
        )

    next_index = (
        get_next_queued_index(
            batch
        )
    )

    if next_index is None:

        raise RuntimeError(
            "No queued simulations remain."
        )

    return start_item(
        batch=batch,
        index=next_index,
    )


# ============================================================
# Refresh currently running item
# ============================================================

def refresh_running_item(
    batch: BatchState,
) -> BatchState:
    """
    Check the currently running CALVADOS simulation.

    If it has ended, update the corresponding batch item.
    """

    running_index = (
        get_running_index(
            batch
        )
    )

    if running_index is None:

        return batch

    item = batch.items[
        running_index
    ]

    summary = get_run_summary(
        Path(
            item.run_dir
        )
    )

    if summary[
        "status"
    ] == "running":

        item.message = (
            summary[
                "message"
            ]
        )

        save_batch(
            batch
        )

        return batch

    item.finished_at = (
        time.time()
    )

    completed_frames = (
        summary[
            "completed_frames"
        ]
    )

    if summary["status"] == "finished" and completed_frames >= item.expected_frames:
        item.status = "finished"
        item.message = "Simulation completed successfully."
    elif summary["status"] == "stopped":
        item.status = "stopped"
        item.message = "Simulation stopped."
    else:
        item.status = "failed"
        item.message = summary.get("message", "Simulation failed.")

    batch.current_index = None

    save_batch(
        batch
    )

    return batch


# ============================================================
# Advance batch
# ============================================================

def advance_batch(
    batch: BatchState,
) -> BatchState:
    """
    Refresh the active simulation and automatically
    start the next queued simulation when appropriate.

    This function is intended to be called repeatedly
    by the Streamlit interface.
    """

    batch = refresh_running_item(
        batch
    )

    running_index = (
        get_running_index(
            batch
        )
    )

    if running_index is not None:

        batch.status = "running"

        save_batch(
            batch
        )

        return batch

    next_index = (
        get_next_queued_index(
            batch
        )
    )

    if next_index is not None:

        batch = start_item(
            batch=batch,
            index=next_index,
        )

        return batch

    # --------------------------------------------------------
    # Nothing running and nothing queued
    # --------------------------------------------------------

    if batch.items:

        all_finished = all(
            item.status
            in {
                "finished",
                "failed",
                "stopped",
            }
            for item in batch.items
        )

        if all_finished:

            batch.status = "finished"

            if batch.finished_at is None:

                batch.finished_at = (
                    time.time()
                )

    save_batch(
        batch
    )

    return batch


# ============================================================
# Batch statistics
# ============================================================

def get_batch_counts(
    batch: BatchState,
) -> dict[str, int]:
    """
    Count simulations by state.
    """

    counts = {
        "total": len(
            batch.items
        ),
        "queued": 0,
        "running": 0,
        "finished": 0,
        "failed": 0,
        "stopped": 0,
    }

    for item in batch.items:

        if item.status in counts:

            counts[
                item.status
            ] += 1

    return counts


# ============================================================
# Overall batch progress
# ============================================================

def get_batch_progress(
    batch: BatchState,
) -> float:
    """
    Estimate overall batch progress.

    Every expected trajectory frame contributes equally.
    """

    total_expected = sum(
        item.expected_frames
        for item in batch.items
    )

    if total_expected <= 0:

        return 0.0

    completed = 0

    for item in batch.items:

        if item.status == "finished":

            completed += (
                item.expected_frames
            )

        elif item.status == "running":

            try:

                summary = (
                    get_run_summary(
                        Path(
                            item.run_dir
                        )
                    )
                )

                completed += min(
                    summary[
                        "completed_frames"
                    ],
                    item.expected_frames,
                )

            except Exception:

                pass

    return min(
        1.0,
        max(
            0.0,
            completed
            / total_expected,
        ),
    )


# ============================================================
# Current simulation summary
# ============================================================

def get_current_summary(
    batch: BatchState,
) -> dict | None:
    """
    Return detailed runner information for the
    currently running simulation.
    """

    running_index = (
        get_running_index(
            batch
        )
    )

    if running_index is None:

        return None

    item = batch.items[
        running_index
    ]

    summary = get_run_summary(
        Path(
            item.run_dir
        )
    )

    summary[
        "name"
    ] = item.name

    summary[
        "queue_index"
    ] = running_index

    summary[
        "queue_total"
    ] = len(
        batch.items
    )

    return summary


# ============================================================
# Estimated batch runtime
# ============================================================

def estimate_batch_remaining_seconds(
    batch: BatchState,
) -> float | None:
    """
    Estimate remaining runtime for the whole batch.

    Once the current simulation has enough progress
    for an ETA, its observed seconds/frame are used
    as an estimate for queued simulations.

    This is deliberately approximate.
    """

    current = get_current_summary(
        batch
    )

    if current is None:

        return None

    completed_frames = (
        current[
            "completed_frames"
        ]
    )

    elapsed_seconds = (
        current[
            "elapsed_seconds"
        ]
    )

    if (
        completed_frames <= 0
        or elapsed_seconds <= 0
    ):

        return None

    seconds_per_frame = (
        elapsed_seconds
        / completed_frames
    )

    remaining_frames = 0

    for item in batch.items:

        if item.status == "queued":

            remaining_frames += (
                item.expected_frames
            )

        elif item.status == "running":

            remaining_frames += max(
                0,
                item.expected_frames
                - completed_frames,
            )

    return (
        remaining_frames
        * seconds_per_frame
    )


# ============================================================
# Standalone diagnostic
# ============================================================

if __name__ == "__main__":

    print(
        "batch.py manages sequential CALVADOS "
        "simulation queues."
    )
