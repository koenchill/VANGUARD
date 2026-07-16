"""Phase 14 — validation artifacts exist and walkthrough reported all-pass."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VAL = REPO / "docs" / "validation"


def test_walkthrough_report_all_passed() -> None:
    report = json.loads((VAL / "section14-walkthrough-report.json").read_text(encoding="utf-8"))
    assert report["all_phases_passed"] is True
    assert len(report["phases"]) == 12
    assert all(p["passed"] for p in report["phases"])


def test_gap_register_keeps_phase4_open() -> None:
    text = (VAL / "gap-closure-register.md").read_text(encoding="utf-8")
    assert "G-020" in text and "Open" in text
    assert "G-021" in text
    assert "G-024" in text
    assert "Local" in text and "G-006" in text
    assert "G-013" in text


def test_checklist_and_go_nogo_exist() -> None:
    assert (VAL / "deliverables-checklist.md").is_file()
    assert (VAL / "go-no-go.md").is_file()
    go = (VAL / "go-no-go.md").read_text(encoding="utf-8")
    assert "G-001" in go
    assert "NO-GO for accreditation" in go or "not ATO" in go.lower() or "No**" in go
