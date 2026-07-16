"""Ongoing incremental / CDC sync path (Section 4 Step 5) — distinct from bulk.

This module is not a special-case of bulk.py. It defines its own job shapes
(scheduled delta DataSync, Debezium-style CDC, event-driven upload) and lands
through the same validation gate.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data_pipelines.ingestion.types import (
    LANDING_PREFIX,
    ObjectManifestEntry,
    TransferBatch,
    TransferPath,
)
from app.data_pipelines.ingestion.validation import (
    ObjectStore,
    record_landed_metadata,
    validate_landing_batch,
)
from app.data_pipelines.db.models import DatasetRecord
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class IncrementalDataSyncJob:
    """Scheduled delta-only DataSync — separate artifact from bulk task configs."""

    job_name: str
    source_location_arn: str
    destination_bucket: str
    schedule_expression: str
    transfer_mode: str = "CHANGED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CdcStreamJob:
    """Debezium-style CDC for relational sources."""

    job_name: str
    connector_class: str
    database_server_name: str
    table_include_list: tuple[str, ...]
    landing_prefix: str = LANDING_PREFIX

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["table_include_list"] = list(self.table_include_list)
        return payload


def write_incremental_datasync_job(path: Path, job: IncrementalDataSyncJob) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(job.to_dict(), indent=2) + "\n", encoding="utf-8")


def write_cdc_stream_job(path: Path, job: CdcStreamJob) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(job.to_dict(), indent=2) + "\n", encoding="utf-8")


def execute_incremental_transfer(
    store: ObjectStore,
    *,
    batch_id: str,
    source_uri: str,
    delta_files: dict[str, bytes],
    mechanism: str = "incremental_datasync",
) -> TransferBatch:
    """Land only the delta set under landing/raw/{batch_id}/."""
    objects: list[ObjectManifestEntry] = []
    for name, data in delta_files.items():
        checksum = hashlib.sha256(data).hexdigest()
        key = f"{LANDING_PREFIX}{batch_id}/{name}"
        store.put_bytes(key, data, checksum)
        objects.append(
            ObjectManifestEntry(key=key, size_bytes=len(data), checksum_sha256=checksum)
        )
    return TransferBatch(
        batch_id=batch_id,
        path=TransferPath.ONGOING,
        source_uri=source_uri,
        objects=objects,
        metadata={
            "store": store,
            "transfer_mechanism": mechanism,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def run_ongoing_sync(
    session: Session,
    store: ObjectStore,
    *,
    batch_id: str,
    source_uri: str,
    delta_files: dict[str, bytes],
    mechanism: str = "incremental_datasync",
    source_manifest: list[ObjectManifestEntry] | None = None,
) -> tuple[TransferBatch, list[DatasetRecord]]:
    """Ongoing path entrypoint — independent of bulk.onboarding."""
    batch = execute_incremental_transfer(
        store,
        batch_id=batch_id,
        source_uri=source_uri,
        delta_files=delta_files,
        mechanism=mechanism,
    )
    manifest = source_manifest or [
        ObjectManifestEntry(
            key=name,
            size_bytes=len(data),
            checksum_sha256=hashlib.sha256(data).hexdigest(),
        )
        for name, data in delta_files.items()
    ]
    result = validate_landing_batch(store, batch, source_manifest=manifest)
    if not result.should_promote:
        return batch, []
    records = record_landed_metadata(session, batch, result)
    session.commit()
    return batch, records
