from calvados_library_builder.motifs import get_default_motifs
from calvados_library_builder.sequences import build_two_motif_design


def test_diblock_sequence_and_length():
    design = build_two_motif_design("VPGVG", 2, "IPAVG", 3, "Diblock", get_default_motifs())
    assert design.sequence == "VPGVG" * 2 + "IPAVG" * 3
    assert design.total_aa == 25
    assert design.motif_counts == {"VPGVG": 2, "IPAVG": 3}
