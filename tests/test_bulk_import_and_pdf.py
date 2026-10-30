"""Bulk library import and PDF overview regression tests."""
from __future__ import annotations

import io

import pandas as pd
import pytest

from calvados_library_builder.bulk_import import parse_sequence_library
from calvados_library_builder.motifs import get_default_motifs
from calvados_library_builder.pdf_report import export_comparison_pdf, motif_runs


def test_bulk_multi_fasta_import():
    rows = parse_sequence_library(">ELP_01\nVPGVGVPGVG\n>ELP_02 some note\nAVTGRGDSPASS\n")
    assert [(r.name, r.sequence) for r in rows] == [
        ("ELP_01", "VPGVGVPGVG"), ("ELP_02", "AVTGRGDSPASS")
    ]


def test_bulk_csv_import_and_errors():
    rows = parse_sequence_library("name,sequence\nfirst,VPGVG\nsecond,IPAVG\n",
                                 filename="screen.csv")
    assert len(rows) == 2
    with pytest.raises(ValueError, match="Duplicate sequence name"):
        parse_sequence_library(">sample 1\nVPGVG\n>sample 2\nIPAVG")
    with pytest.raises(ValueError, match="Sequence 2"):
        parse_sequence_library(">good\nVPGVG\n>bad\nNOT_A_PROTEIN")
    with pytest.raises(ValueError, match="must have"):
        parse_sequence_library("one,two\nx,y", filename="screen.csv")


def test_pdf_motif_runs_use_actual_sequence():
    motifs = get_default_motifs()
    runs = motif_runs("VPGVG" * 5 + "AVTGRGDSPASS" + "IPAVG" * 2, motifs)
    assert runs == [("VPGVG", 5), ("RGD", 1), ("IPAVG", 2)]


def test_vector_pdf_report_complete(tmp_path):
    frame = pd.DataFrame([
        {
            "name": "ELP1", "sequence": "VPGVG" * 5,
            "fraction_collapsed": .5, "mean_rg_nm": 2.9,
            "mean_rg_collapsed_nm": 2.4,
            "k_collapse_per_ns": .1, "k_escape_per_ns": .2,
        },
        {
            "name": "ELP2", "sequence": "AVTGRGDSPASS" + "IPAVG" * 3,
            "fraction_collapsed": .8, "mean_rg_nm": 3.1,
            "mean_rg_collapsed_nm": 2.7,
            "k_collapse_per_ns": .04, "k_escape_per_ns": .08,
        },
    ])
    pdf = export_comparison_pdf(frame)
    assert pdf[:8] == b"%PDF-1."
    assert len(pdf) > 8000
    outfile = tmp_path / "comparison.pdf"
    outfile.write_bytes(pdf)
    assert outfile.is_file()


def test_pdf_rejects_missing_metrics():
    with pytest.raises(ValueError, match="Missing analysis columns"):
        export_comparison_pdf(pd.DataFrame([{"name": "x", "sequence": "VPGVG"}]))
