"""Build-side RLS simulation for dual-path BI (Section 5 / G-004 / §14 Phase 6).

Trino+OPA enforces classification / mission_id filters using the *end-user*
identity forwarded by Kerberos (PowerBI) or oauthPassThru (Grafana).
This module proves two principals see different row counts on the same mart —
fail-closed when identity is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Principal:
    name: str
    classification: str  # e.g. U // FOUO / SECRET
    mission_ids: frozenset[str]


@dataclass(frozen=True)
class MartRow:
    dataset_version: str
    mission_id: str
    classification: str
    quality_score: float


# Classification ordinal — higher may see lower when policy allows read-down.
_CLASS_RANK = {"U": 0, "FOUO": 1, "SECRET": 2, "TS": 3}


def _rank(label: str) -> int:
    return _CLASS_RANK[label.upper()]


def filter_rows_for_principal(
    rows: Iterable[MartRow],
    principal: Principal | None,
    *,
    fail_closed: bool = True,
) -> list[MartRow]:
    """OPA-equivalent row filter. Missing identity → deny all when fail_closed."""
    if principal is None:
        if fail_closed:
            return []
        raise ValueError("identity required")

    allowed: list[MartRow] = []
    for row in rows:
        if row.mission_id not in principal.mission_ids:
            continue
        if _rank(row.classification) > _rank(principal.classification):
            continue
        allowed.append(row)
    return allowed


def row_counts_for_two_identities(
    rows: list[MartRow],
    user_a: Principal,
    user_b: Principal,
) -> tuple[int, int]:
    a = len(filter_rows_for_principal(rows, user_a))
    b = len(filter_rows_for_principal(rows, user_b))
    return a, b


def sample_mart_rows() -> list[MartRow]:
    """Synthetic mart rows aligned to Phase 6 sample (build-side evidence)."""
    return [
        MartRow("v1", "mission-alpha", "U", 0.91),
        MartRow("v2", "mission-alpha", "FOUO", 0.88),
        MartRow("v3", "mission-alpha", "SECRET", 0.85),
        MartRow("v4", "mission-bravo", "U", 0.93),
        MartRow("v5", "mission-bravo", "FOUO", 0.80),
        MartRow("v6", "mission-charlie", "SECRET", 0.77),
    ]


# Canonical test principals — one per BI path acceptance scenario.
ANALYST_ALPHA = Principal(
    name="analyst.alpha@mission.internal",
    classification="FOUO",
    mission_ids=frozenset({"mission-alpha"}),
)
ANALYST_BRAVO = Principal(
    name="analyst.bravo@mission.internal",
    classification="SECRET",
    mission_ids=frozenset({"mission-bravo", "mission-charlie"}),
)
