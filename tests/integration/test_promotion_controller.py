"""Unit/integration tests for G-014 atomic promotion and lineage."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.data_pipelines.db.models import ActiveDatasetPointer, CurationStage, DatasetRecord
from app.data_pipelines.db.session import create_db_engine, init_schema, session_factory
from app.data_pipelines.lineage import InMemoryLakeFS, record_lineage, resolve_version
from app.data_pipelines.promotion import (
    PromotionArtifacts,
    PromotionError,
    compensate_rollback,
    get_active_version,
    promote,
    resolve_queryable_version,
    stage_candidate,
)


@pytest.fixture()
def db_session():
    engine = create_db_engine("sqlite+pysqlite:///:memory:")
    init_schema(engine)
    Session = session_factory(engine)
    with Session() as session:
        yield session


def _artifacts(version: str, **kwargs) -> PromotionArtifacts:
    base = dict(
        dataset_version=version,
        source_uri=f"s3://lake/landing/raw/{version}",
        lakefs_commit_id=f"commit-{version}",
        vector_snapshot_id=f"vec-{version}",
        model_prompt_digest=f"digest-{version}",
        quality_score=0.95,
    )
    base.update(kwargs)
    return PromotionArtifacts(**base)


def test_lineage_round_trip() -> None:
    client = InMemoryLakeFS()
    ref = record_lineage(
        client,
        branch="curation",
        dataset_version="v1",
        source_uri="s3://src/a",
        parent_version=None,
    )
    resolved = resolve_version(client, ref.lakefs_commit_id)
    assert resolved.dataset_version == "v1"
    assert resolved.source_uri == "s3://src/a"


def test_promote_flips_pointer_atomically(db_session) -> None:
    stage_candidate(db_session, _artifacts("v1"))
    db_session.commit()
    assert get_active_version(db_session) is None

    promote(db_session, "v1")
    assert get_active_version(db_session) == "v1"
    assert resolve_queryable_version(db_session, "v1") == "v1"
    assert resolve_queryable_version(db_session, "v2") is None


def test_fault_injection_before_pointer_flip_leaves_prior_active(db_session) -> None:
    stage_candidate(db_session, _artifacts("v1"))
    promote(db_session, "v1")
    assert get_active_version(db_session) == "v1"

    stage_candidate(db_session, _artifacts("v2"))
    db_session.commit()

    def boom(phase: str) -> None:
        if phase == "after_mark_promoting":
            raise RuntimeError("injected kill mid-switch")

    with pytest.raises(RuntimeError, match="injected kill"):
        promote(db_session, "v2", fail_before=boom)

    db_session.rollback()
    # Prior active version remains the only queryable version.
    assert get_active_version(db_session) == "v1"
    assert resolve_queryable_version(db_session, "v2") is None
    # Candidate must not be resolvable as active.
    v2 = db_session.scalar(select(DatasetRecord).where(DatasetRecord.dataset_version == "v2"))
    assert v2 is not None
    assert v2.curation_stage in {CurationStage.approved, CurationStage.promoting}


def test_fault_injection_after_flip_before_commit_rolls_back(db_session) -> None:
    stage_candidate(db_session, _artifacts("v1"))
    promote(db_session, "v1")

    stage_candidate(db_session, _artifacts("v2"))
    db_session.commit()

    def boom(phase: str) -> None:
        if phase == "after_pointer_flip":
            raise RuntimeError("crash before commit")

    with pytest.raises(RuntimeError, match="crash before commit"):
        promote(db_session, "v2", fail_before=boom)

    db_session.rollback()
    assert get_active_version(db_session) == "v1"
    assert resolve_queryable_version(db_session, "v2") is None


def test_compensate_rollback_orphans_candidate(db_session) -> None:
    stage_candidate(db_session, _artifacts("v9"))
    db_session.commit()
    compensate_rollback(db_session, "v9")
    db_session.commit()
    row = db_session.scalar(select(DatasetRecord).where(DatasetRecord.dataset_version == "v9"))
    assert row.curation_stage == CurationStage.orphaned
    assert row.is_active_candidate is False
    assert resolve_queryable_version(db_session, "v9") is None


def test_low_quality_candidate_rejected(db_session) -> None:
    stage_candidate(db_session, _artifacts("bad", quality_score=0.2))
    db_session.commit()
    with pytest.raises(PromotionError, match="quality"):
        promote(db_session, "bad")
