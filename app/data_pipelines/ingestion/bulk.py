"""One-time bulk transfer path (Section 4 Step 3) — distinct from ongoing sync.

Uses DataSync (network) or Snowball (when DataSync ETA exceeds acceptable onboarding
window). Always writes to landing/raw/ only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.data_pipelines.ingestion.types import (
    LANDING_PREFIX,
    ObjectManifestEntry,
    TransferBatch,
    TransferPath,
)
from app.data_pipelines.ingestion.validation import (
    InMemoryObjectStore,
    ObjectStore,
    record_landed_metadata,
    validate_landing_batch,
)
from app.data_pipelines.db.models import DatasetRecord
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class DataSyncTaskConfig:
    """Declarative DataSync task — bulk only (not reused by incremental jobs)."""

    task_name: str
    source_location_arn: str
    destination_bucket: str
    destination_subdirectory: str = "/landing/raw"
    verify_mode: str = "ONLY_FILES_TRANSFERRED"
    includes: tuple[str, ...] = ("**",)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SnowballJobConfig:
    """Physical appliance path when network transfer exceeds onboarding window."""

    job_name: str
    landing_bucket: str
    landing_prefix: str = LANDING_PREFIX
    onboarding_window_days: int = 14

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_datasync_task_config(path: Path, config: DataSyncTaskConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_dict(), indent=2) + "\n", encoding="utf-8")


def write_snowball_job_config(path: Path, config: SnowballJobConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_dict(), indent=2) + "\n", encoding="utf-8")


def execute_bulk_transfer(
    store: ObjectStore,
    *,
    batch_id: str,
    source_uri: str,
    source_files: dict[str, bytes],
) -> TransferBatch:
    """Simulate bulk DataSync/Snowball landing into landing/raw/{batch_id}/."""
    objects: list[ObjectManifestEntry] = []
    for name, data in source_files.items():
        checksum = hashlib.sha256(data).hexdigest()
        key = f"{LANDING_PREFIX}{batch_id}/{name}"
        store.put_bytes(key, data, checksum)
        objects.append(
            ObjectManifestEntry(key=key, size_bytes=len(data), checksum_sha256=checksum)
        )
    return TransferBatch(
        batch_id=batch_id,
        path=TransferPath.BULK,
        source_uri=source_uri,
        objects=objects,
        metadata={"store": store, "transfer_mechanism": "datasync_or_snowball"},
    )


def run_bulk_onboarding(
    session: Session,
    store: ObjectStore,
    *,
    batch_id: str,
    source_uri: str,
    source_files: dict[str, bytes],
    source_manifest: list[ObjectManifestEntry] | None = None,
) -> tuple[TransferBatch, list[DatasetRecord]]:
    """Bulk path entrypoint: transfer → validate → land metadata (or quarantine)."""
    batch = execute_bulk_transfer(
        store,
        batch_id=batch_id,
        source_uri=source_uri,
        source_files=source_files,
    )
    manifest = source_manifest or [
        ObjectManifestEntry(
            key=name,
            size_bytes=len(data),
            checksum_sha256=hashlib.sha256(data).hexdigest(),
        )
        for name, data in source_files.items()
    ]
    result = validate_landing_batch(store, batch, source_manifest=manifest)
    if not result.should_promote:
        return batch, []
    records = record_landed_metadata(session, batch, result)
    session.commit()
    return batch, records
