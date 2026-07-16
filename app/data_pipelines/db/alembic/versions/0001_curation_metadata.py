"""empty message

Revision ID: 0001_curation_metadata
Revises:
Create Date: 2026-07-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_curation_metadata"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_version", sa.String(length=128), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column(
            "curation_stage",
            sa.Enum(
                "landed",
                "deduped",
                "pii_scrubbed",
                "labeled",
                "pending_hitl",
                "approved",
                "rejected",
                "promoting",
                "active",
                "orphaned",
                name="curation_stage",
            ),
            nullable=False,
        ),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("pii_scan_result", sa.String(length=64), nullable=True),
        sa.Column("drift_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "hitl_approval_status",
            sa.Enum(
                "not_required",
                "pending",
                "approved",
                "rejected",
                name="hitl_approval_status",
            ),
            nullable=False,
        ),
        sa.Column("lineage_parent_id", sa.Integer(), sa.ForeignKey("dataset_records.id"), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lakefs_commit_id", sa.String(length=128), nullable=True),
        sa.Column("vector_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("model_prompt_digest", sa.String(length=128), nullable=True),
        sa.Column("is_active_candidate", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_dataset_records_dataset_version", "dataset_records", ["dataset_version"])

    op.create_table(
        "active_dataset_pointer",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("singleton_key", sa.String(length=32), nullable=False),
        sa.Column("active_dataset_version", sa.String(length=128), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("singleton_key", name="uq_active_singleton"),
    )

    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("mission_id", sa.String(length=128), nullable=False),
        sa.Column("step_name", sa.String(length=128), nullable=False),
        sa.Column("dataset_version", sa.String(length=128), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("telemetry_events")
    op.drop_table("active_dataset_pointer")
    op.drop_index("ix_dataset_records_dataset_version", table_name="dataset_records")
    op.drop_table("dataset_records")
    sa.Enum(name="curation_stage").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="hitl_approval_status").drop(op.get_bind(), checkfirst=True)
