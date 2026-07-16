"""G-006 — signed recovery-set manifests; stale component rejection."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from tools.recovery_set import (
    ComponentCatalog,
    ManifestError,
    ManifestSigner,
    capture_checkpoint,
    restore_from_manifest,
    write_manifest,
)

REPO = Path(__file__).resolve().parents[2]


def _signer_and_manifest(**overrides):
    signer = ManifestSigner()
    signer.create_key("recovery-1")
    fields = dict(
        cadence="daily",
        delta_table_version="delta-v42",
        rds_recovery_point="rds:rp-20260716",
        velero_backup_id="velero-backup-77",
        milvus_vector_checkpoint="milvus-ckpt-9",
        model_prompt_digest="sha256:model-prompt-1",
        opa_policy_bundle_digest="sha256:opa-bundle-1",
        schema_migration_version="alembic:rev-00a1",
        clock=datetime(2026, 7, 16, 18, 0, tzinfo=timezone.utc),
    )
    fields.update(overrides)
    comps = capture_checkpoint(**fields)
    manifest = signer.sign("recovery-1", comps)
    return signer, manifest


def _catalog_for(manifest) -> ComponentCatalog:
    c = manifest.components
    return ComponentCatalog(
        delta_table_versions={c.delta_table_version},
        rds_recovery_points={c.rds_recovery_point},
        velero_backup_ids={c.velero_backup_id},
        milvus_checkpoints={c.milvus_vector_checkpoint},
        model_prompt_digests={c.model_prompt_digest},
        opa_policy_bundle_digests={c.opa_policy_bundle_digest},
        schema_migration_versions={c.schema_migration_version},
    )


def test_restore_from_consistent_manifest() -> None:
    signer, manifest = _signer_and_manifest()
    plan = restore_from_manifest(manifest, _catalog_for(manifest), signer)
    assert plan["status"] == "restore_plan_accepted"
    assert plan["delta_table_version"] == "delta-v42"


def test_stale_manifest_component_rejected() -> None:
    signer, manifest = _signer_and_manifest()
    catalog = _catalog_for(manifest)
    catalog.delta_table_versions = {"delta-v99-current"}  # v42 is stale
    with pytest.raises(ManifestError, match="stale or unknown delta_table_version"):
        restore_from_manifest(manifest, catalog, signer)


def test_tampered_manifest_signature_rejected() -> None:
    signer, manifest = _signer_and_manifest()
    bad = type(manifest)(
        components=manifest.components,
        content_digest=manifest.content_digest,
        signature_hex="00" * 64,
        key_id=manifest.key_id,
    )
    with pytest.raises(ManifestError, match="signature"):
        restore_from_manifest(bad, _catalog_for(manifest), signer)


def test_write_manifest_roundtrip(tmp_path: Path) -> None:
    signer, manifest = _signer_and_manifest()
    path = tmp_path / "daily-test.json"
    write_manifest(path, manifest)
    from tools.recovery_set import load_manifest

    loaded = load_manifest(path)
    assert loaded.content_digest == manifest.content_digest
    signer.verify(loaded)


def test_daily_weekly_policies_require_manifest() -> None:
    for name in ("daily", "weekly"):
        policy = yaml.safe_load(
            (REPO / "backup-dr" / name / "policy.yaml").read_text(encoding="utf-8")
        )
        assert policy["produces_recovery_set_manifest"] is True
        assert "delta_table_version" in policy["components"]
