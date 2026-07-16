"""G-018 evidence-grade audit pipeline — hash-chained, WORM, trusted time."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


class AuditError(Exception):
    """Fail-closed audit integrity error."""


TRUSTED_CLOCK: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

GENESIS_HASH = "0" * 64


@dataclass
class AuditEvent:
    event_id: str
    event_type: str
    occurred_at: str
    actor: dict[str, str]
    payload: dict[str, Any]
    integrity: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at,
            "actor": self.actor,
            "payload": self.payload,
            "integrity": self.integrity,
        }


def _event_hash(prev_hash: str, body: dict[str, Any]) -> str:
    material = {
        "prev_hash": prev_hash,
        "event_id": body["event_id"],
        "event_type": body["event_type"],
        "occurred_at": body["occurred_at"],
        "actor": body["actor"],
        "payload": body["payload"],
    }
    blob = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


@dataclass
class WormAuditStore:
    """Append-only WORM stand-in (S3 Object Lock compliance mode in cloud)."""

    path: Path
    role: str = "operator"  # operator | evidence_reader
    _revoked_keys: set[str] = field(default_factory=set)
    clock: Callable[[], datetime] = field(default_factory=lambda: TRUSTED_CLOCK)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def _read_all(self) -> list[dict[str, Any]]:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def _append_raw(self, event: dict[str, Any]) -> None:
        # WORM: no overwrite API — only append.
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")

    def last_hash(self) -> str:
        events = self._read_all()
        if not events:
            return GENESIS_HASH
        return events[-1]["integrity"]["event_hash"]

    def append(
        self,
        *,
        event_type: str,
        actor: dict[str, str],
        payload: dict[str, Any],
        client_supplied_time: str | None = None,
    ) -> AuditEvent:
        if client_supplied_time is not None:
            raise AuditError("client-supplied timestamps are rejected — use trusted clock")
        if self.role != "operator":
            raise AuditError("evidence_reader cannot append audit events")
        prev = self.last_hash()
        body = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "occurred_at": self.clock().isoformat(),
            "actor": actor,
            "payload": payload,
        }
        event_hash = _event_hash(prev, body)
        integrity = {
            "prev_hash": prev,
            "event_hash": event_hash,
            "destination": "s3_object_lock_worm",
        }
        event = AuditEvent(**body, integrity=integrity)
        self._append_raw(event.to_dict())
        return event

    def verify_chain(self) -> None:
        events = self._read_all()
        prev = GENESIS_HASH
        seen_ids: set[str] = set()
        for event in events:
            eid = event["event_id"]
            if eid in seen_ids:
                raise AuditError(f"duplicate-event: {eid}")
            seen_ids.add(eid)
            if event["integrity"]["prev_hash"] != prev:
                raise AuditError("hash chain broken (tamper or missing-event)")
            expected = _event_hash(prev, event)
            if event["integrity"]["event_hash"] != expected:
                raise AuditError("event_hash mismatch (tamper)")
            prev = event["integrity"]["event_hash"]

    def detect_deletion_gap(self) -> None:
        """Deletion from the middle breaks prev_hash linkage."""
        self.verify_chain()

    def read_as_evidence(self) -> list[dict[str, Any]]:
        if self.role not in {"evidence_reader", "operator"}:
            raise AuditError("unauthorized audit read")
        # Operators can write; evidence readers are the distinct review role (G-018).
        self.verify_chain()
        return self._read_all()

    def simulate_tamper(self, index: int, field: str, value: Any) -> None:
        """Test helper — mutate a stored event (WORM would block this in AWS)."""
        events = self._read_all()
        events[index][field] = value
        self.path.write_text(
            "\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n",
            encoding="utf-8",
        )

    def simulate_deletion(self, index: int) -> None:
        events = self._read_all()
        del events[index]
        self.path.write_text(
            "\n".join(json.dumps(e, sort_keys=True) for e in events) + ("\n" if events else ""),
            encoding="utf-8",
        )

    def simulate_replay(self, index: int) -> None:
        events = self._read_all()
        events.append(events[index])
        self.path.write_text(
            "\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n",
            encoding="utf-8",
        )


def assert_clock_skew_rejected(store: WormAuditStore, skewed: datetime) -> None:
    """Trusted clock only — callers cannot pass occurred_at."""
    try:
        store.append(
            event_type="admin_change",
            actor={"principal": "x", "tenant": "t"},
            payload={},
            client_supplied_time=skewed.isoformat(),
        )
    except AuditError:
        return
    raise AssertionError("expected client-supplied time rejection")
