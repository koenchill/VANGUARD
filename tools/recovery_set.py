"""G-006 signed recovery-set manifest — bind all restore components at one checkpoint."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


class ManifestError(Exception):
    """Fail-closed recovery-set error."""


@dataclass(frozen=True)
class RecoverySetComponents:
    checkpoint_id: str
    captured_at: str
    delta_table_version: str
    rds_recovery_point: str
    velero_backup_id: str
    milvus_vector_checkpoint: str
    model_prompt_digest: str
    opa_policy_bundle_digest: str
    schema_migration_version: str
    cadence: str  # daily | weekly

    def content_digest(self) -> str:
        payload = asdict(self)
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()


@dataclass(frozen=True)
class SignedRecoveryManifest:
    components: RecoverySetComponents
    content_digest: str
    signature_hex: str
    key_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "components": asdict(self.components),
            "content_digest": self.content_digest,
            "signature_hex": self.signature_hex,
            "key_id": self.key_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SignedRecoveryManifest:
        return cls(
            components=RecoverySetComponents(**data["components"]),
            content_digest=data["content_digest"],
            signature_hex=data["signature_hex"],
            key_id=data["key_id"],
        )


class ManifestSigner:
    """KMS/HSM stand-in for recovery-set signatures."""

    def __init__(self) -> None:
        self._keys: dict[str, Ed25519PrivateKey] = {}
        self._pubs: dict[str, Ed25519PublicKey] = {}

    def create_key(self, key_id: str) -> None:
        private = Ed25519PrivateKey.generate()
        self._keys[key_id] = private
        self._pubs[key_id] = private.public_key()

    def sign(self, key_id: str, components: RecoverySetComponents) -> SignedRecoveryManifest:
        if key_id not in self._keys:
            raise ManifestError(f"unknown signing key: {key_id}")
        digest = components.content_digest()
        sig = self._keys[key_id].sign(bytes.fromhex(digest))
        return SignedRecoveryManifest(
            components=components,
            content_digest=digest,
            signature_hex=sig.hex(),
            key_id=key_id,
        )

    def verify(self, manifest: SignedRecoveryManifest) -> None:
        pub = self._pubs.get(manifest.key_id)
        if pub is None:
            raise ManifestError(f"unknown verify key: {manifest.key_id}")
        expected = manifest.components.content_digest()
        if expected != manifest.content_digest:
            raise ManifestError("content_digest mismatch — manifest tampered")
        try:
            pub.verify(
                bytes.fromhex(manifest.signature_hex),
                bytes.fromhex(manifest.content_digest),
            )
        except Exception as exc:  # noqa: BLE001
            raise ManifestError("signature verification failed") from exc


def capture_checkpoint(
    *,
    cadence: str,
    delta_table_version: str,
    rds_recovery_point: str,
    velero_backup_id: str,
    milvus_vector_checkpoint: str,
    model_prompt_digest: str,
    opa_policy_bundle_digest: str,
    schema_migration_version: str,
    clock: datetime | None = None,
) -> RecoverySetComponents:
    if cadence not in {"daily", "weekly"}:
        raise ManifestError("cadence must be daily or weekly")
    now = clock or datetime.now(timezone.utc)
    checkpoint_id = f"{cadence}-{now.strftime('%Y%m%dT%H%M%SZ')}"
    return RecoverySetComponents(
        checkpoint_id=checkpoint_id,
        captured_at=now.isoformat(),
        delta_table_version=delta_table_version,
        rds_recovery_point=rds_recovery_point,
        velero_backup_id=velero_backup_id,
        milvus_vector_checkpoint=milvus_vector_checkpoint,
        model_prompt_digest=model_prompt_digest,
        opa_policy_bundle_digest=opa_policy_bundle_digest,
        schema_migration_version=schema_migration_version,
        cadence=cadence,
    )


def write_manifest(path: Path, manifest: SignedRecoveryManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> SignedRecoveryManifest:
    return SignedRecoveryManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))


@dataclass
class ComponentCatalog:
    """Live component IDs available for restore — used to reject stale references."""

    delta_table_versions: set[str]
    rds_recovery_points: set[str]
    velero_backup_ids: set[str]
    milvus_checkpoints: set[str]
    model_prompt_digests: set[str]
    opa_policy_bundle_digests: set[str]
    schema_migration_versions: set[str]


def validate_manifest_for_restore(
    manifest: SignedRecoveryManifest,
    catalog: ComponentCatalog,
    signer: ManifestSigner,
) -> None:
    """Restore always uses a verified manifest; stale component refs are rejected first."""
    signer.verify(manifest)
    c = manifest.components
    checks = [
        (c.delta_table_version, catalog.delta_table_versions, "delta_table_version"),
        (c.rds_recovery_point, catalog.rds_recovery_points, "rds_recovery_point"),
        (c.velero_backup_id, catalog.velero_backup_ids, "velero_backup_id"),
        (c.milvus_vector_checkpoint, catalog.milvus_checkpoints, "milvus_vector_checkpoint"),
        (c.model_prompt_digest, catalog.model_prompt_digests, "model_prompt_digest"),
        (
            c.opa_policy_bundle_digest,
            catalog.opa_policy_bundle_digests,
            "opa_policy_bundle_digest",
        ),
        (
            c.schema_migration_version,
            catalog.schema_migration_versions,
            "schema_migration_version",
        ),
    ]
    for value, allowed, name in checks:
        if value not in allowed:
            raise ManifestError(f"stale or unknown {name}: {value}")


def restore_from_manifest(
    manifest: SignedRecoveryManifest,
    catalog: ComponentCatalog,
    signer: ManifestSigner,
) -> dict[str, str]:
    """Compose a coherent restore plan — never mix independently selected backups."""
    validate_manifest_for_restore(manifest, catalog, signer)
    c = manifest.components
    return {
        "checkpoint_id": c.checkpoint_id,
        "delta_table_version": c.delta_table_version,
        "rds_recovery_point": c.rds_recovery_point,
        "velero_backup_id": c.velero_backup_id,
        "milvus_vector_checkpoint": c.milvus_vector_checkpoint,
        "model_prompt_digest": c.model_prompt_digest,
        "opa_policy_bundle_digest": c.opa_policy_bundle_digest,
        "schema_migration_version": c.schema_migration_version,
        "status": "restore_plan_accepted",
    }
