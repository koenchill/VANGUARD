"""Per-agent-step telemetry into the curation metadata DB (Section 5 / Phase 6 schema)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.data_pipelines.db.models import TelemetryEvent


class TelemetryLogger:
    def __init__(self, session: Session | None = None) -> None:
        self._session = session
        self.events: list[dict[str, Any]] = []

    def log_step(
        self,
        *,
        agent_id: str,
        mission_id: str,
        step_name: str,
        payload: dict[str, Any],
        dataset_version: str | None = None,
    ) -> None:
        record = {
            "agent_id": agent_id,
            "mission_id": mission_id,
            "step_name": step_name,
            "dataset_version": dataset_version,
            "payload": payload,
        }
        self.events.append(record)
        if self._session is not None:
            self._session.add(
                TelemetryEvent(
                    agent_id=agent_id,
                    mission_id=mission_id,
                    step_name=step_name,
                    dataset_version=dataset_version,
                    payload_json=json.dumps(payload, sort_keys=True),
                )
            )
            self._session.flush()
