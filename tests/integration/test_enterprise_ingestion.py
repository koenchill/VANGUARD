"""Phase 7 enterprise ingestion — bulk vs ongoing paths and quarantine gate."""

from __future__ import annotations

import hashlib
import inspect

import pytest
from sqlalchemy import select

from app.data_pipelines.db.models import CurationStage, DatasetRecord
from app.data_pipelines.db.session import create_db_engine, init_schema, session_factory
from app.data_pipelines import ingestion as ingestion_pkg
from app.data_pipelines.ingestion import bulk as bulk_mod
from app.data_pipelines.ingestion import ongoing as ongoing_mod
from app.data_pipelines.ingestion.types import LANDING_PREFIX, QUARANTINE_PREFIX, ObjectManifestEntry
from app.data_pipelines.ingestion.validation import InMemoryObjectStore, validate_landing_batch


@pytest.fixture()
def db_session():
    engine = create_db_engine("sqlite+pysqlite:///:memory:")
    init_schema(engine)
    Session = session_factory(engine)
    with Session() as session:
        yield session


def test_bulk_and_ongoing_are_separate_modules() -> None:
    assert inspect.getmodule(bulk_mod.run_bulk_onboarding) is bulk_mod
    assert inspect.getmodule(ongoing_mod.run_ongoing_sync) is ongoing_mod
    assert bulk_mod.run_bulk_onboarding.__code__ is not ongoing_mod.run_ongoing_sync.__code__
    # Ongoing must not import bulk entrypoint (no special-case reuse).
    assert "run_bulk_onboarding" not in dir(ongoing_mod)
    assert "run_ongoing_sync" not in dir(bulk_mod)


def test_bulk_reconciles_and_lands(db_session) -> None:
    store = InMemoryObjectStore()
    files = {"a.parquet": b"bulk-aaaa", "b.parquet": b"bulk-bbbb"}
    batch, records = bulk_mod.run_bulk_onboarding(
        db_session,
        store,
        batch_id="bulk-001",
        source_uri="s3://enterprise-source/mission",
        source_files=files,
    )
    assert batch.path.value == "bulk"
    assert len(records) == 2
    assert all(r.curation_stage == CurationStage.landed for r in records)
    assert all(r.dataset_version.startswith("bulk-") for r in records)


def test_corrupted_file_is_quarantined_not_promoted(db_session) -> None:
    store = InMemoryObjectStore()
    good = b"good-payload"
    bad = b"truncated"
    # Land objects manually with a wrong checksum relative to source manifest.
    store.put_bytes(
        f"{LANDING_PREFIX}bulk-bad/good.parquet",
        good,
        hashlib.sha256(good).hexdigest(),
    )
    store.put_bytes(
        f"{LANDING_PREFIX}bulk-bad/corrupt.parquet",
        bad,
        hashlib.sha256(bad).hexdigest(),
    )
    from app.data_pipelines.ingestion.types import TransferBatch, TransferPath

    batch = TransferBatch(
        batch_id="bulk-bad",
        path=TransferPath.BULK,
        source_uri="s3://enterprise-source/mission",
        metadata={"store": store},
    )
    source_manifest = [
        ObjectManifestEntry(
            key="good.parquet",
            size_bytes=len(good),
            checksum_sha256=hashlib.sha256(good).hexdigest(),
        ),
        ObjectManifestEntry(
            key="corrupt.parquet",
            size_bytes=len(bad) + 100,  # source claims larger → mismatch
            checksum_sha256=hashlib.sha256(b"full-original-bytes").hexdigest(),
        ),
    ]
    result = validate_landing_batch(store, batch, source_manifest=source_manifest)
    assert result.should_promote is False
    assert any(k.startswith(QUARANTINE_PREFIX) for k in result.quarantined_keys)
    # Quarantined object removed from landing.
    landing_keys = [o.key for o in store.list_prefix(f"{LANDING_PREFIX}bulk-bad/")]
    assert not any(k.endswith("corrupt.parquet") for k in landing_keys)


def test_ongoing_sync_produces_distinct_landed_rows(db_session) -> None:
    store = InMemoryObjectStore()
    bulk_mod.run_bulk_onboarding(
        db_session,
        store,
        batch_id="bulk-100",
        source_uri="s3://enterprise-source/mission",
        source_files={"base.parquet": b"base"},
    )
    ongoing_mod.run_ongoing_sync(
        db_session,
        store,
        batch_id="cdc-200",
        source_uri="s3://enterprise-source/mission",
        delta_files={"delta-1.json": b'{"id":1}'},
        mechanism="cdc",
    )
    rows = db_session.scalars(select(DatasetRecord)).all()
    bulk_rows = [r for r in rows if r.dataset_version.startswith("bulk-")]
    ongoing_rows = [r for r in rows if r.dataset_version.startswith("ongoing-")]
    assert len(bulk_rows) == 1
    assert len(ongoing_rows) == 1
    assert all(r.curation_stage == CurationStage.landed for r in rows)


def test_cannot_write_curated_zones_from_transfer_store() -> None:
    store = InMemoryObjectStore()
    with pytest.raises(PermissionError):
        store.put_bytes("bronze/x.parquet", b"nope", hashlib.sha256(b"nope").hexdigest())


def test_package_exports_both_paths() -> None:
    assert hasattr(ingestion_pkg, "run_bulk_onboarding")
    assert hasattr(ingestion_pkg, "run_ongoing_sync")
