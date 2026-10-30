"""Work around OpenMM checkpoint replacement failures on some Windows drives.

OpenMM 8.4's filename-based saveCheckpoint uses safesave.save(), which
moves/renames an existing checkpoint on every update. Some Windows storage
setups deny this rename (WinError 5), even though normal file writes work.

Within CALVADOS child processes only, pass an opened file object to
Simulation.saveCheckpoint(). OpenMM explicitly supports this interface and
skips safesave's rename operations. Existing checkpoints are backed up before
overwriting. This is NOT an atomic write: preserve .previous if a process
crashes mid-checkpoint.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Callable


def install_checkpoint_compat(
    simulation_class: type | None = None,
    *,
    windows: bool | None = None,
) -> bool:
    """Patch checkpoint *file naming* only, without altering simulation physics.

    In production this is enabled only on Windows and only inside the child
    process that runs CALVADOS. `simulation_class` and `windows` allow unit
    testing with a stand-in OpenMM class on non-Windows CI.
    """
    windows = os.name == "nt" if windows is None else windows
    if not windows:
        return False

    if simulation_class is None:
        from openmm.app import Simulation
        simulation_class = Simulation

    original: Callable[..., Any] = simulation_class.saveCheckpoint
    if getattr(original, "_elp_windows_checkpoint_patch", False):
        return True

    def save_checkpoint(self: Any, file: Any) -> None:
        # OpenMM already supports streams. Only named checkpoints need a fix.
        if not isinstance(file, (str, os.PathLike)):
            return original(self, file)

        filename = Path(file)
        filename.parent.mkdir(parents=True, exist_ok=True)
        backup = filename.with_name(filename.name + ".previous")

        # Keep the previous complete checkpoint for recovery if the new write
        # is interrupted. The backup is copied, not renamed, avoiding the
        # Windows access-denied problem. Never delete this useful backup.
        if filename.is_file():
            shutil.copyfile(filename, backup)

        # OpenMM's saveCheckpoint(file_handle) uses createCheckpoint() and
        # file_handle.write(), bypassing the failing safesave rename path.
        with filename.open("wb") as handle:
            original(self, handle)
            handle.flush()
            os.fsync(handle.fileno())

    save_checkpoint._elp_windows_checkpoint_patch = True  # type: ignore[attr-defined]
    simulation_class.saveCheckpoint = save_checkpoint
    return True
