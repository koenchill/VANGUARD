"""Atomic staged promotion controller (G-014).

Build non-active artifacts → validate → atomically flip one active_dataset_version
pointer. Interrupted promotion leaves the previous active version intact;
compensating rollback marks orphaned candidates rather than leaving them queryable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_pipelines.db.models import (
    ActiveDatasetPointer,
    CurationStage,
    DatasetRecord,
    HitlApprovalStatus,
)


class PromotionError(RuntimeError):
    pass


@dataclass(frozen=True)
class PromotionArtifacts:
    dataset_version: str
    source_uri: str
    lakefs_commit_id: str
    vector_snapshot_id: str
    model_prompt_digest: str
    quality_score: float
    lineage_parent_id: int | None = None


InjectedFailure = Callable[[str], None]


def _noop_failure(_phase: str) -> None:
    return None


def ensure_pointer(session: Session) -> ActiveDatasetPointer:
    pointer = session.scalar(
        select(ActiveDatasetPointer).where(ActiveDatasetPointer.singleton_key == "active")
    )
    if pointer is None:
        pointer = ActiveDatasetPointer(singleton_key="active", active_dataset_version=None)
        session.add(pointer)
        session.flush()
    return pointer


def get_active_version(session: Session) -> str | None:
    pointer = ensure_pointer(session)
    return pointer.active_dataset_version


def resolve_queryable_version(session: Session, requested: str | None = None) -> str | None:
    """Consumers may only resolve the active pointer — never partial candidates."""
    active = get_active_version(session)
    if requested is None:
        return active
    if requested != active:
        return None
    return active


def stage_candidate(session: Session, artifacts: PromotionArtifacts) -> DatasetRecord:
    record = DatasetRecord(
        dataset_version=artifacts.dataset_version,
        source_uri=artifacts.source_uri,
        curation_stage=CurationStage.approved,
        quality_score=artifacts.quality_score,
        pii_scan_result="clean",
        drift_flag=False,
        hitl_approval_status=HitlApprovalStatus.approved,
        lineage_parent_id=artifacts.lineage_parent_id,
        approved_at=datetime.now(timezone.utc),
        lakefs_commit_id=artifacts.lakefs_commit_id,
        vector_snapshot_id=artifacts.vector_snapshot_id,
        model_prompt_digest=artifacts.model_prompt_digest,
        is_active_candidate=True,
    )
    session.add(record)
    session.flush()
    return record


def _validate_candidate(session: Session, dataset_version: str) -> DatasetRecord:
    record = session.scalar(
        select(DatasetRecord).where(
            DatasetRecord.dataset_version == dataset_version,
            DatasetRecord.is_active_candidate.is_(True),
        )
    )
    if record is None:
        raise PromotionError(f"no staged candidate for {dataset_version}")
    if record.curation_stage not in {CurationStage.approved, CurationStage.promoting}:
        raise PromotionError(f"candidate {dataset_version} not approved")
    if not record.lakefs_commit_id or not record.vector_snapshot_id:
        raise PromotionError(f"candidate {dataset_version} missing lineage/vector artifacts")
    if record.quality_score is None or record.quality_score < 0.7:
        raise PromotionError(f"candidate {dataset_version} failed quality gate")
    return record


def compensate_rollback(session: Session, dataset_version: str) -> None:
    record = session.scalar(
        select(DatasetRecord).where(DatasetRecord.dataset_version == dataset_version)
    )
    if record is None:
        return
    record.curation_stage = CurationStage.orphaned
    record.is_active_candidate = False
    session.flush()


def promote(
    session: Session,
    dataset_version: str,
    *,
    fail_before: InjectedFailure = _noop_failure,
) -> str:
    """Atomically flip the active pointer after validation.

    ``fail_before`` is invoked with a phase name to support fault-injection tests.
    Any exception before commit leaves the prior active version unchanged.
    """
    pointer = ensure_pointer(session)
    previous = pointer.active_dataset_version
    candidate = _validate_candidate(session, dataset_version)

    candidate.curation_stage = CurationStage.promoting
    session.flush()
    fail_before("after_mark_promoting")

    # Single atomic switch of the pointer — nothing else is queryable mid-flight.
    pointer.active_dataset_version = candidate.dataset_version
    candidate.curation_stage = CurationStage.active
    candidate.is_active_candidate = False
    session.flush()
    fail_before("after_pointer_flip")

    session.commit()
    fail_before("after_commit")
    return previous or ""
