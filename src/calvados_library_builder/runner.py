#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import time

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


# ============================================================
# Files used by the runner
# ============================================================

RUNNER_STATE_FILENAME = "runner_state.json"
RUNNER_LOG_FILENAME = "run.log"
RUNNER_STDERR_FILENAME = "run_error.log"


# ============================================================
# Run state
# ============================================================

@dataclass
class RunState:
    """
    Persistent state for one CALVADOS simulation.
    """

    run_dir: str

    status: str = "prepared"

    pid: int | None = None

    started_at: float | None = None
    finished_at: float | None = None

    expected_frames: int | None = None
    completed_frames: int = 0

    return_code: int | None = None

    command: list[str] | None = None

    message: str = ""


# ============================================================
# Paths
# ============================================================

def get_state_path(
    run_dir: Path,
) -> Path:
    """
    Path to the persistent runner state JSON file.
    """

    return (
        Path(run_dir)
        / RUNNER_STATE_FILENAME
    )


def get_log_path(
    run_dir: Path,
) -> Path:
    """
    Path to stdout log.
    """

    return (
        Path(run_dir)
        / RUNNER_LOG_FILENAME
    )


def get_error_log_path(
    run_dir: Path,
) -> Path:
    """
    Path to stderr log.
    """

    return (
        Path(run_dir)
        / RUNNER_STDERR_FILENAME
    )


# ============================================================
# State persistence
# ============================================================

def save_run_state(
    state: RunState,
) -> None:
    """
    Save runner state as JSON inside the simulation directory.
    """

    path = get_state_path(
        Path(state.run_dir)
    )

    path.write_text(
        json.dumps(
            asdict(state),
            indent=2,
        ),
        encoding="utf-8",
    )


def load_run_state(
    run_dir: Path,
) -> RunState:
    """
    Load persistent run state.

    If no state file exists, return a default prepared state.
    """

    run_dir = Path(
        run_dir
    ).resolve()

    state_path = get_state_path(
        run_dir
    )

    if not state_path.exists():

        return RunState(
            run_dir=str(run_dir),
            status="prepared",
        )

    data = json.loads(
        state_path.read_text(
            encoding="utf-8"
        )
    )

    return RunState(
        **data
    )


# ============================================================
# Process helpers
# ============================================================

def process_exists(
    pid: int | None,
) -> bool:
    """
    Check whether a process with the supplied PID exists.
    """

    if pid is None:
        return False

    try:

        if os.name == "nt":

            creationflags = 0

            if hasattr(
                subprocess,
                "CREATE_NO_WINDOW",
            ):

                creationflags = (
                    subprocess.CREATE_NO_WINDOW
                )

            result = subprocess.run(
                [
                    "tasklist",
                    "/FI",
                    f"PID eq {pid}",
                ],
                capture_output=True,
                text=True,
                creationflags=creationflags,
            )

            return (
                str(pid)
                in result.stdout
            )

        os.kill(
            pid,
            0,
        )

        return True

    except Exception:

        return False


# ============================================================
# CALVADOS run.py discovery
# ============================================================

def find_run_script(
    run_dir: Path,
) -> Path:
    """
    Find the CALVADOS run.py script inside a prepared folder.
    """

    run_dir = Path(
        run_dir
    ).resolve()

    direct_path = (
        run_dir
        / "run.py"
    )

    if direct_path.exists():

        return direct_path

    candidates = list(
        run_dir.glob(
            "**/run.py"
        )
    )

    if not candidates:

        raise FileNotFoundError(
            f"No run.py found inside {run_dir}"
        )

    if len(candidates) > 1:

        raise RuntimeError(
            "Multiple run.py files found inside "
            f"{run_dir}. Expected exactly one."
        )

    return candidates[0]


# ============================================================
# Trajectory discovery
# ============================================================

def find_trajectory(
    run_dir: Path,
) -> Path | None:
    """
    Locate the most recently modified DCD trajectory
    inside the run directory.
    """

    run_dir = Path(
        run_dir
    )

    candidates = list(
        run_dir.glob(
            "**/*.dcd"
        )
    )

    if not candidates:

        return None

    valid_candidates = []

    for candidate in candidates:

        try:

            if candidate.exists():

                valid_candidates.append(
                    candidate
                )

        except OSError:

            continue

    if not valid_candidates:

        return None

    valid_candidates.sort(
        key=lambda path: (
            path.stat().st_mtime
        ),
        reverse=True,
    )

    return valid_candidates[0]


# ============================================================
# DCD frame counting
# ============================================================

def count_dcd_frames(
    trajectory_path: Path,
) -> int:
    """
    Read the number of frames directly from the DCD header.

    This avoids opening an actively written trajectory with
    MDAnalysis.

    Standard DCD files contain the number of coordinate sets
    (NSET) at byte offset 8.

    The first integer is normally 84 and is used here to
    detect byte order.
    """

    trajectory_path = Path(
        trajectory_path
    )

    if not trajectory_path.exists():

        return 0

    try:

        # A partially created DCD may exist before the full
        # header has been written.
        file_size = (
            trajectory_path
            .stat()
            .st_size
        )

        if file_size < 12:

            return 0

        with trajectory_path.open(
            "rb"
        ) as handle:

            header_start = (
                handle.read(
                    4
                )
            )

            signature = (
                handle.read(
                    4
                )
            )

            nset_bytes = (
                handle.read(
                    4
                )
            )


        # ----------------------------------------------------
        # Ensure we actually received enough bytes.
        # ----------------------------------------------------

        if (
            len(header_start) != 4
            or len(signature) != 4
            or len(nset_bytes) != 4
        ):

            return 0


        # ----------------------------------------------------
        # Determine byte order.
        #
        # Typical DCD header begins with integer 84.
        # ----------------------------------------------------

        little_header = (
            struct.unpack(
                "<i",
                header_start,
            )[0]
        )

        big_header = (
            struct.unpack(
                ">i",
                header_start,
            )[0]
        )

        if little_header == 84:

            endian = "<"

        elif big_header == 84:

            endian = ">"

        else:

            # File may temporarily be between writes,
            # or it may not be a standard DCD.
            return 0


        # ----------------------------------------------------
        # Standard coordinate trajectories use CORD.
        #
        # Some DCD variants may use VELD.
        # ----------------------------------------------------

        if signature not in {
            b"CORD",
            b"VELD",
        }:

            return 0


        # ----------------------------------------------------
        # NSET
        # ----------------------------------------------------

        n_frames = (
            struct.unpack(
                f"{endian}i",
                nset_bytes,
            )[0]
        )

        return max(
            0,
            int(
                n_frames
            ),
        )


    except (
        OSError,
        PermissionError,
        struct.error,
        ValueError,
    ):

        # OpenMM might be writing at exactly this moment.
        # The next Streamlit refresh will simply try again.
        return 0


# ============================================================
# Progress estimation
# ============================================================

def estimate_completed_frames(
    run_dir: Path,
) -> int:
    """
    Estimate completed frames from the current DCD trajectory.
    """

    trajectory = find_trajectory(
        run_dir
    )

    if trajectory is None:

        return 0

    return count_dcd_frames(
        trajectory
    )


# ============================================================
# Runtime calculations
# ============================================================

def get_elapsed_seconds(
    state: RunState,
) -> float:
    """
    Return elapsed wall-clock time.
    """

    if state.started_at is None:

        return 0.0

    end_time = (
        state.finished_at
        if state.finished_at is not None
        else time.time()
    )

    return max(
        0.0,
        end_time
        - state.started_at,
    )


def get_progress_fraction(
    state: RunState,
) -> float:
    """
    Progress between 0 and 1.
    """

    if (
        state.expected_frames is None
        or state.expected_frames <= 0
    ):

        return 0.0

    return min(
        1.0,
        max(
            0.0,
            state.completed_frames
            / state.expected_frames,
        ),
    )


def estimate_total_seconds(
    state: RunState,
) -> float | None:
    """
    Estimate total runtime using observed simulation progress.
    """

    fraction = (
        get_progress_fraction(
            state
        )
    )

    elapsed = (
        get_elapsed_seconds(
            state
        )
    )

    if (
        fraction <= 0
        or elapsed <= 0
    ):

        return None

    return (
        elapsed
        / fraction
    )


def estimate_remaining_seconds(
    state: RunState,
) -> float | None:
    """
    Estimate remaining simulation time.
    """

    estimated_total = (
        estimate_total_seconds(
            state
        )
    )

    if estimated_total is None:

        return None

    remaining = (
        estimated_total
        - get_elapsed_seconds(
            state
        )
    )

    return max(
        0.0,
        remaining,
    )


# ============================================================
# Human-readable time
# ============================================================

def format_duration(
    seconds: float | None,
) -> str:
    """
    Convert seconds into a compact readable duration.
    """

    if seconds is None:

        return "Calculating..."

    seconds = int(
        max(
            0,
            seconds,
        )
    )

    days, remainder = divmod(
        seconds,
        86400,
    )

    hours, remainder = divmod(
        remainder,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    if days > 0:

        return (
            f"{days} d "
            f"{hours} h "
            f"{minutes} min"
        )

    if hours > 0:

        return (
            f"{hours} h "
            f"{minutes} min"
        )

    if minutes > 0:

        return (
            f"{minutes} min "
            f"{seconds} s"
        )

    return (
        f"{seconds} s"
    )


# ============================================================
# Start simulation
# ============================================================

def start_run(
    run_dir: Path,
    expected_frames: int | None = None,
) -> RunState:
    """
    Launch CALVADOS run.py as a subprocess.

    stdout and stderr are written into files in the
    simulation directory.
    """

    run_dir = Path(
        run_dir
    ).resolve()

    if not run_dir.exists():

        raise FileNotFoundError(
            f"Run directory does not exist: {run_dir}"
        )


    # --------------------------------------------------------
    # Avoid launching the same simulation twice.
    # --------------------------------------------------------

    previous_state = (
        load_run_state(
            run_dir
        )
    )

    if (
        previous_state.status
        == "running"
        and process_exists(
            previous_state.pid
        )
    ):

        raise RuntimeError(
            "This simulation is already running."
        )


    # --------------------------------------------------------
    # Find CALVADOS launcher
    # --------------------------------------------------------

    run_script = (
        find_run_script(
            run_dir
        )
    )


    # --------------------------------------------------------
    # Logging
    # --------------------------------------------------------

    log_path = (
        get_log_path(
            run_dir
        )
    )

    error_log_path = (
        get_error_log_path(
            run_dir
        )
    )

    command = [
        sys.executable,
        run_script.name,
    ]


    log_handle = open(
        log_path,
        "a",
        encoding="utf-8",
        buffering=1,
    )

    error_handle = open(
        error_log_path,
        "a",
        encoding="utf-8",
        buffering=1,
    )


    timestamp = (
        datetime.now()
        .isoformat(
            timespec="seconds"
        )
    )

    log_handle.write(
        "\n"
        + "=" * 70
        + "\n"
    )

    log_handle.write(
        f"CALVADOS run started: "
        f"{timestamp}\n"
    )

    log_handle.write(
        f"Working directory: "
        f"{run_script.parent}\n"
    )

    log_handle.write(
        f"Command: "
        f"{' '.join(command)}\n"
    )

    log_handle.write(
        "=" * 70
        + "\n"
    )

    log_handle.flush()


    # --------------------------------------------------------
    # Windows process flags
    # --------------------------------------------------------

    creationflags = 0

    if os.name == "nt":

        if hasattr(
            subprocess,
            "CREATE_NEW_PROCESS_GROUP",
        ):

            creationflags |= (
                subprocess.CREATE_NEW_PROCESS_GROUP
            )

        if hasattr(
            subprocess,
            "CREATE_NO_WINDOW",
        ):

            creationflags |= (
                subprocess.CREATE_NO_WINDOW
            )


    # --------------------------------------------------------
    # Launch
    # --------------------------------------------------------

    try:

        process = subprocess.Popen(
            command,

            cwd=str(
                run_script.parent
            ),

            stdout=log_handle,

            stderr=error_handle,

            stdin=subprocess.DEVNULL,

            creationflags=creationflags,
        )

    except Exception:

        log_handle.close()
        error_handle.close()

        raise


    # Parent process no longer needs its own file handles.
    # The child process has inherited them.
    log_handle.close()
    error_handle.close()


    # --------------------------------------------------------
    # Persist state
    # --------------------------------------------------------

    state = RunState(
        run_dir=str(
            run_dir
        ),

        status="running",

        pid=process.pid,

        started_at=time.time(),

        expected_frames=(
            expected_frames
        ),

        completed_frames=0,

        command=command,

        message=(
            "CALVADOS simulation running."
        ),
    )

    save_run_state(
        state
    )

    return state


# ============================================================
# Refresh state
# ============================================================

def refresh_run_state(
    run_dir: Path,
) -> RunState:
    """
    Refresh process status and trajectory progress.
    """

    run_dir = Path(
        run_dir
    ).resolve()

    state = (
        load_run_state(
            run_dir
        )
    )


    # --------------------------------------------------------
    # Update frame progress.
    # --------------------------------------------------------

    detected_frames = (
        estimate_completed_frames(
            run_dir
        )
    )

    # Avoid the displayed progress moving backwards if a read
    # temporarily fails while OpenMM is updating the file.
    state.completed_frames = max(
        state.completed_frames,
        detected_frames,
    )


    # --------------------------------------------------------
    # Process state
    # --------------------------------------------------------

    if state.status == "running":

        alive = (
            process_exists(
                state.pid
            )
        )

        if not alive:

            state.finished_at = (
                state.finished_at
                or time.time()
            )


            # ------------------------------------------------
            # At this stage we only know the process ended.
            #
            # Since Streamlit does not retain the original
            # Popen object between reruns, we cannot reliably
            # query its return code here.
            # ------------------------------------------------

            if (
                state.expected_frames
                is not None
                and state.completed_frames
                >= state.expected_frames
            ):

                state.status = (
                    "finished"
                )

                state.message = (
                    "Simulation completed."
                )

            else:

                state.status = (
                    "finished"
                )

                state.message = (
                    "Simulation process ended."
                )

