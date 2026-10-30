"""Tests for motif canvas's canonical Python state and thesis color palette."""
from __future__ import annotations

import pytest

from calvados_library_builder.motifs import create_motif, get_default_motifs
from calvados_library_builder.studio_sequence import (
    default_groups, extract_single_fasta, groups_to_architecture,
    groups_to_sequence, load_custom_motifs, normalize_groups,
    save_custom_motifs, segment_raw_sequence, load_draft, save_draft,
)


def test_default_colors_and_single_sequence():
    motifs = get_default_motifs()
    assert motifs["VPGVG"].color == "#4C78A8"
    assert motifs["IPAVG"].color == "#F2CF5B"
    assert motifs["VPGIG"].color == "#54A24B"
    assert motifs["VPGKG"].color == "#C13CFF"
    assert motifs["VPGEG"].color == "#F28E2B"
    assert motifs["VPAVG"].color == "#FF66B3"
    assert groups_to_sequence(default_groups(), motifs) == "VPGVG" * 10
    assert motifs["RGD"].color == "#7944AC"
    assert motifs["RGD"].sequence == "AVTGRGDSPASS"


def test_reordering_merging_and_splitting_preserve_exact_order():
    motifs = get_default_motifs()
    groups = [
        {"segments": [{"motif": "VPGKG", "count": 2}, {"motif": "VPGEG", "count": 1}]},
        {"segments": [{"motif": "VPGVG", "count": 3}]},
    ]
    assert groups_to_sequence(groups, motifs) == "VPGKG" * 2 + "VPGEG" + "VPGVG" * 3
    assert groups_to_architecture(groups, motifs) == "VPGKG×2 | VPGEG×1 | VPGVG×3"
    assert len(normalize_groups(groups, motifs)) == 3
    reordered = [groups[1], groups[0]]
    assert groups_to_sequence(reordered, motifs) == "VPGVG" * 3 + "VPGKG" * 2 + "VPGEG"


def test_adjacent_identical_blocks_coalesce_and_split_is_stable():
    motifs = get_default_motifs()
    chunks = [
        {"segments": [{"motif": "VPGVG", "count": 2}]},
        {"segments": [{"motif": "VPGVG", "count": 3}]},
        {"segments": [{"motif": "IPAVG", "count": 1}]},
    ]
    joined = normalize_groups(chunks, motifs)
    assert len(joined) == 2
    assert joined[0]["segments"][0]["count"] == 5
    split = [
        {"segments": [{"motif": "VPGVG", "count": 2}]},
        {"segments": [{"motif": "VPGVG", "count": 3}], "split_before": True},
    ]
    result = normalize_groups(split, motifs)
    assert len(result) == 2
    assert groups_to_sequence(split, motifs) == "VPGVG" * 5
    assert groups_to_architecture(split, motifs) == "VPGVG×2 | VPGVG×3"


def test_elp_draft_persists_across_sessions(tmp_path):
    path = tmp_path / "current_draft.json"
    motifs = get_default_motifs()
    groups = [
        {"segments": [{"motif": "VPGVG", "count": 5}]},
        {"segments": [{"motif": "RGD", "count": 1}]},
    ]
    save_draft(path, "my_rgdelp", groups, motifs)
    restored_name, restored_blocks = load_draft(path, motifs)
    assert restored_name == "my_rgdelp"
    assert restored_blocks == groups
    assert groups_to_sequence(restored_blocks, motifs) == "VPGVG" * 5 + "AVTGRGDSPASS"


def test_fasta_import_roundtrip_with_unknown_fragment():
    motifs = get_default_motifs()
    source = "VPGVG" * 2 + "AAAA" + "IPAVG"
    groups, fragments = segment_raw_sequence(f">experiment\n{source}\n", motifs)
    assert len(fragments) == 1
    assert groups_to_sequence(groups, {**motifs, **fragments}) == source
    assert extract_single_fasta("VPGVG\nIPAVG") == "VPGVGIPAVG"
    with pytest.raises(ValueError, match="one FASTA"):
        extract_single_fasta(">a\nVPGVG\n>b\nIPAVG")


def test_custom_motifs_persist_without_changing_defaults(tmp_path):
    path = tmp_path / "custom_motifs.json"
    addition = create_motif("vpgfg", "VPGFG", "#00AEEF")
    save_custom_motifs(path, {"VPGFG": addition})
    found = load_custom_motifs(path)
    assert found["VPGFG"] == addition
    with pytest.raises(ValueError, match="Cannot override thesis motif colors"):
        save_custom_motifs(path, {"VPGVG": create_motif("VPGVG", "VPGVG", "#000000")})


def test_reject_corrupt_or_oversized_groups():
    motifs = get_default_motifs()
    with pytest.raises(ValueError, match="Unknown motif"):
        groups_to_sequence([{"segments": [{"motif": "UNKNOWN", "count": 1}]}], motifs)
    with pytest.raises(ValueError, match="Repeat count"):
        groups_to_sequence([{"segments": [{"motif": "VPGVG", "count": 0}]}], motifs)
