"""Staging designs before simulation preparation, without losing edits."""
from __future__ import annotations

import json

import pytest

from calvados_library_builder.designs import Candidate
from calvados_library_builder.bulk_import import parse_sequence_library
from calvados_library_builder.design_collection import (
    add_to_collection, remove_from_collection, next_design_name,
    save_collection, load_collection,
)
from calvados_library_builder.replicates import build_run_plan


def design(name: str, motif: str = "VPGVG", repeats: int = 10) -> Candidate:
    return Candidate(name, motif * repeats, f"{motif} × {repeats}")


def test_staging_multiple_designs_before_prepare(tmp_path):
    first = design("ELP_01")
    collected = add_to_collection([], [first])
    second = design("ELP_02", "IPAVG")
    collected = add_to_collection(collected, [second])

    # An edited canvas does not change already-staged sequence snapshots.
    second = design("ELP_02", "VPGKG")
    assert collected[1].sequence == "IPAVG" * 10
    assert next_design_name(collected) == "ELP_03"

    save_path = tmp_path / "saved_collection.json"
    save_collection(save_path, collected)
    restored = load_collection(save_path)
    assert restored == collected
    assert [p.sequence_name for p in build_run_plan(restored, tmp_path / "batch")] == [
        "ELP_01", "ELP_02"
    ]


def test_bulk_import_appends_to_collection(tmp_path):
    staged = add_to_collection([], [design("manually_built")])
    imported = parse_sequence_library(">import_A\nVPGVGVPGVG\n>import_B\nIPAVGIPAVG\n")
    staged = add_to_collection(staged, imported)
    assert len(staged) == 3
    assert len(build_run_plan(staged, tmp_path / "experiment", triplicate=True)) == 9


def test_duplicate_names_are_rejected_without_mutating_original(tmp_path):
    original = [design("ELP_01")]
    with pytest.raises(ValueError, match="already in the collection"):
        add_to_collection(original, [design("elp_01", "IPAVG")])
    assert original[0].sequence == "VPGVG" * 10
    with pytest.raises(ValueError, match="already in the collection"):
        add_to_collection([], [design("a"), design("A")])
    assert next_design_name([design("ELP_01"), design("ELP_03")]) == "ELP_02"


def test_remove_or_clear_only_staged_designs(tmp_path):
    saved = tmp_path / "staged.json"
    save_collection(saved, [design("a"), design("b"), design("c")])
    subset = remove_from_collection(load_collection(saved), "B")
    assert [c.name for c in subset] == ["a", "c"]
    save_collection(saved, subset)
    assert [c.name for c in load_collection(saved)] == ["a", "c"]
    save_collection(saved, [])
    assert load_collection(saved) == []
    with pytest.raises(ValueError, match="not found"):
        remove_from_collection([], "missing")


def test_invalid_collection_does_not_overwrite_existing(tmp_path):
    saved = tmp_path / "staged.json"
    save_collection(saved, [design("valid")])
    before = saved.read_bytes()
    with pytest.raises(ValueError, match="Invalid design name"):
        save_collection(saved, [design("space name")])
    assert saved.read_bytes() == before


def test_missing_or_corrupt_collection(tmp_path):
    path = tmp_path / "collection.json"
    assert load_collection(path) == []
    path.write_text(json.dumps({"version": 2, "designs": []}))
    with pytest.raises(ValueError, match="Unsupported"):
        load_collection(path)
