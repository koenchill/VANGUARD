"""Shared landing-zone models and constants (Section 4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


LANDING_PREFIX = "landing/raw/"
QUARANTINE_PREFIX = "landing/quarantine/"
CURATED_PREFIXES = ("bronze/", "silver/", "gold/")


class TransferPath(str, Enum):
    """Distinct code paths — never collapse bulk into ongoing or vice versa."""

    BULK = "bulk"
    ONGOING = "ongoing"


@dataclass(frozen=True)
class ObjectManifestEntry:
    key: str
    size_bytes: int
    checksum_sha256: str


@dataclass
class TransferBatch:
    batch_id: str
    path: TransferPath
    source_uri: str
    objects: list[ObjectManifestEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    ok: bool
    batch_id: str
    path: TransferPath
    expected_count: int
    actual_count: int
    mismatched_checksums: list[str] = field(default_factory=list)
    quarantined_keys: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def should_promote(self) -> bool:
        return self.ok and not self.quarantined_keys and not self.errors
