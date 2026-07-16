"""EXPLAIN full-scan CI gate helper tests."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.check_explain_full_scan import plan_has_full_table_scan  # noqa: E402


def test_detects_seq_scan() -> None:
    assert plan_has_full_table_scan("Seq Scan on curated_datasets")


def test_passes_index_scan() -> None:
    assert not plan_has_full_table_scan("Index Scan using curated_datasets_pkey")


def test_sample_bad_plan_fixture() -> None:
    fixture = Path(__file__).parent / "fixtures" / "explain_full_scan.txt"
    assert plan_has_full_table_scan(fixture.read_text(encoding="utf-8"))
