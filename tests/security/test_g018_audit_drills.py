"""G-018 audit drills — tamper, deletion, replay (minimum gate) + related checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from security.grc.audit_pipeline import AuditError, WormAuditStore, assert_clock_skew_rejected

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture()
def store(tmp_path: Path) -> WormAuditStore:
    return WormAuditStore(path=tmp_path / "audit.jsonl", role="operator")


def _seed(store: WormAuditStore, n: int = 3) -> None:
    for i in range(n):
        store.append(
            event_type="tool_call",
            actor={"principal": f"agent-{i}", "tenant": "mission-tenant"},
            payload={"i": i},
        )


def test_hash_chain_verifies_clean_log(store: WormAuditStore) -> None:
    _seed(store)
    store.verify_chain()
    assert len(store.read_as_evidence()) == 3


def test_tamper_drill_detected(store: WormAuditStore) -> None:
    _seed(store)
    store.simulate_tamper(1, "payload", {"i": 999, "evil": True})
    with pytest.raises(AuditError, match="tamper"):
        store.verify_chain()


def test_deletion_drill_detected(store: WormAuditStore) -> None:
    _seed(store)
    store.simulate_deletion(1)
    with pytest.raises(AuditError):
        store.detect_deletion_gap()


def test_replay_drill_detected(store: WormAuditStore) -> None:
    _seed(store)
    store.simulate_replay(0)
    with pytest.raises(AuditError, match="duplicate"):
        store.verify_chain()


def test_client_supplied_clock_rejected(store: WormAuditStore) -> None:
    assert_clock_skew_rejected(store, datetime.now(timezone.utc) - timedelta(days=30))


def test_evidence_reader_cannot_append(tmp_path: Path) -> None:
    reader = WormAuditStore(path=tmp_path / "audit.jsonl", role="evidence_reader")
    with pytest.raises(AuditError, match="evidence_reader"):
        reader.append(
            event_type="admin_change",
            actor={"principal": "auditor", "tenant": "t"},
            payload={},
        )


def test_iam_role_separation_artifacts_exist() -> None:
    reader = (REPO / "security" / "grc" / "iam-evidence-reader.json").read_text(encoding="utf-8")
    operator = (REPO / "security" / "grc" / "iam-operator.json").read_text(encoding="utf-8")
    assert "Deny" in reader and "DeleteObject" in reader
    assert "PutObject" in operator
    assert "DeleteObject" in operator  # denied for operators too on WORM
