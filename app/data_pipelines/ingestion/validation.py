"""Landing-zone validation — checksum/count reconciliation + quarantine (Section 4 Step 4).

Both bulk and ongoing paths call this gate. There is no fast path that skips validation.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

from app.data_pipelines.db.models import CurationStage, DatasetRecord, HitlApprovalStatus
from app.data_pipelines.ingestion.types import (
    CURATED_PREFIXES,
    LANDING_PREFIX,
    QUARANTINE_PREFIX,
    ObjectManifestEntry,
    TransferBatch,
    TransferPath,
    ValidationResult,
)
from sqlalchemy.orm import Session


class ObjectStore(Protocol):
    def list_prefix(self, prefix: str) -> list[ObjectManifestEntry]: ...

    def get_bytes(self, key: str) -> bytes: ...

    def move(self, src_key: str, dest_key: str) -> None: ...

    def put_bytes(self, key: str, data: bytes, checksum_sha256: str) -> None: ...


class InMemoryObjectStore:
    """Local stand-in for S3 landing/quarantine buckets in tests."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put_bytes(self, key: str, data: bytes, checksum_sha256: str) -> None:
        digest = hashlib.sha256(data).hexdigest()
        if digest != checksum_sha256:
            raise ValueError(f"checksum mismatch on put for {key}")
        if any(key.startswith(p) for p in CURATED_PREFIXES):
            raise PermissionError("transfer path cannot write curated zones")
        self._objects[key] = data

    def get_bytes(self, key: str) -> bytes:
        return self._objects[key]

    def list_prefix(self, prefix: str) -> list[ObjectManifestEntry]:
        out: list[ObjectManifestEntry] = []
        for key, data in self._objects.items():
            if key.startswith(prefix):
                out.append(
                    ObjectManifestEntry(
                        key=key,
                        size_bytes=len(data),
                        checksum_sha256=hashlib.sha256(data).hexdigest(),
                    )
                )
        return sorted(out, key=lambda e: e.key)

    def move(self, src_key: str, dest_key: str) -> None:
        data = self._objects.pop(src_key)
        self._objects[dest_key] = data


def _assert_landing_only(keys: list[str]) -> list[str]:
    errors: list[str] = []
    for key in keys:
        if not key.startswith(LANDING_PREFIX):
            errors.append(f"object not under {LANDING_PREFIX}: {key}")
        if any(key.startswith(p) for p in CURATED_PREFIXES):
            errors.append(f"object illegally targets curated zone: {key}")
    return errors


def validate_landing_batch(
    store: ObjectStore,
    batch: TransferBatch,
    *,
    source_manifest: list[ObjectManifestEntry],
) -> ValidationResult:
    """Reconcile source vs landing; quarantine mismatches; never silent-promote."""
    landing_objects = store.list_prefix(f"{LANDING_PREFIX}{batch.batch_id}/")
    landing_by_name = {o.key.split("/")[-1]: o for o in landing_objects}
    source_by_name = {o.key.split("/")[-1]: o for o in source_manifest}

    errors = _assert_landing_only([o.key for o in landing_objects])
    mismatched: list[str] = []
    quarantined: list[str] = []

    if len(landing_objects) != len(source_manifest):
        errors.append(
            f"count mismatch: source={len(source_manifest)} landing={len(landing_objects)}"
        )

    for name, src in source_by_name.items():
        landed = landing_by_name.get(name)
        if landed is None:
            errors.append(f"missing in landing: {name}")
            continue
        if landed.checksum_sha256 != src.checksum_sha256:
            mismatched.append(landed.key)
            qkey = landed.key.replace(LANDING_PREFIX, QUARANTINE_PREFIX, 1)
            store.move(landed.key, qkey)
            quarantined.append(qkey)
            errors.append(f"checksum mismatch quarantined: {name}")
        elif landed.size_bytes != src.size_bytes:
            mismatched.append(landed.key)
            qkey = landed.key.replace(LANDING_PREFIX, QUARANTINE_PREFIX, 1)
            store.move(landed.key, qkey)
            quarantined.append(qkey)
            errors.append(f"size mismatch quarantined: {name}")

    # Deliberately corrupted / truncated files already handled above.
    ok = not errors and not quarantined
    return ValidationResult(
        ok=ok,
        batch_id=batch.batch_id,
        path=batch.path,
        expected_count=len(source_manifest),
        actual_count=len(landing_objects),
        mismatched_checksums=mismatched,
        quarantined_keys=quarantined,
        errors=errors,
    )


def record_landed_metadata(
    session: Session,
    batch: TransferBatch,
    result: ValidationResult,
) -> list[DatasetRecord]:
    """Populate curation_stage='landed' only for validated objects (Section 4 Step 4)."""
    if not result.should_promote:
        raise ValueError(f"refusing to land failed batch {batch.batch_id}: {result.errors}")

    store: ObjectStore | None = batch.metadata.get("store")
    if store is None:
        raise ValueError("batch.metadata['store'] required to enumerate landed objects")

    records: list[DatasetRecord] = []
    for entry in store.list_prefix(f"{LANDING_PREFIX}{batch.batch_id}/"):
        version = f"{batch.path.value}-{batch.batch_id}-{entry.key.split('/')[-1]}"
        rec = DatasetRecord(
            dataset_version=version,
            source_uri=f"{batch.source_uri}#{entry.key}",
            curation_stage=CurationStage.landed,
            quality_score=None,
            pii_scan_result="pending",
            drift_flag=False,
            hitl_approval_status=HitlApprovalStatus.not_required,
            lakefs_commit_id=None,
        )
        session.add(rec)
        records.append(rec)
    session.flush()
    return records
