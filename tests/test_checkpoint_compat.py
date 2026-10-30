"""Windows checkpoint compatibility tests without GPU or an OpenMM context."""
from __future__ import annotations

import os

from calvados_library_builder.checkpoint_compat import install_checkpoint_compat


def test_windows_checkpoint_saves_through_stream_and_preserves_backup(tmp_path):
    class FakeSimulation:
        def __init__(self):
            self.counter = 0

        def saveCheckpoint(self, target):
            # This test fails if our patch passes a string back into OpenMM.
            assert hasattr(target, "write")
            self.counter += 1
            target.write(f"checkpoint-{self.counter}".encode("ascii"))

    assert install_checkpoint_compat(FakeSimulation, windows=True)
    assert install_checkpoint_compat(FakeSimulation, windows=True)  # idempotent
    sim = FakeSimulation()
    ckpt = tmp_path / "restart.chk"
    sim.saveCheckpoint(str(ckpt))
    assert ckpt.read_bytes() == b"checkpoint-1"
    assert not (tmp_path / "restart.chk.previous").exists()
    sim.saveCheckpoint(ckpt)
    assert ckpt.read_bytes() == b"checkpoint-2"
    assert (tmp_path / "restart.chk.previous").read_bytes() == b"checkpoint-1"
    assert list(tmp_path.glob("restart.chk.*.tmp")) == []


def test_other_platform_unmodified():
    class FakeSimulation:
        def saveCheckpoint(self, target):
            return target

    original = FakeSimulation.saveCheckpoint
    assert not install_checkpoint_compat(FakeSimulation, windows=False)
    assert FakeSimulation.saveCheckpoint is original
