"""Curation metadata ORM models (Section 3)."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CurationStage(str, enum.Enum):
    landed = "landed"
    deduped = "deduped"
    pii_scrubbed = "pii_scrubbed"
    labeled = "labeled"
    pending_hitl = "pending_hitl"
    approved = "approved"
    rejected = "rejected"
    promoting = "promoting"
    active = "active"
    orphaned = "orphaned"


class HitlApprovalStatus(str, enum.Enum):
    not_required = "not_required"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class DatasetRecord(Base):
    __tablename__ = "dataset_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_version: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    curation_stage: Mapped[CurationStage] = mapped_column(
        Enum(CurationStage, name="curation_stage"),
        nullable=False,
        default=CurationStage.landed,
    )
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    pii_scan_result: Mapped[str | None] = mapped_column(String(64), nullable=True)
    drift_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hitl_approval_status: Mapped[HitlApprovalStatus] = mapped_column(
        Enum(HitlApprovalStatus, name="hitl_approval_status"),
        nullable=False,
        default=HitlApprovalStatus.pending,
    )
    lineage_parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("dataset_records.id"), nullable=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lakefs_commit_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    vector_snapshot_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_prompt_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active_candidate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    parent = relationship("DatasetRecord", remote_side=[id], uselist=False)


class ActiveDatasetPointer(Base):
    """Single-row pointer — the only version consumers may resolve (G-014)."""

    __tablename__ = "active_dataset_pointer"
    __table_args__ = (UniqueConstraint("singleton_key", name="uq_active_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    singleton_key: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    active_dataset_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TelemetryEvent(Base):
    """Per-agent-step events that feed sql/marts/reporting (Section 5)."""

    __tablename__ = "telemetry_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mission_id: Mapped[str] = mapped_column(String(128), nullable=False)
    step_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
