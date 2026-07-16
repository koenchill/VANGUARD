"""AI Gateway policy loader — Kong declarative / Mosaic-compatible."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

POLICIES_PATH = Path(__file__).with_name("policies.yaml")

# G-012 approved handling levels (ADR: docs/adrs/model-boundary.md)
APPROVED_CLASSIFICATIONS = frozenset({"U", "FOUO"})
DEFAULT_APPROVED_EGRESS = frozenset(
    {
        "model.inference.vpc.internal",
        "model-fallback.inference.vpc.internal",
    }
)


class ModelBoundaryDenied(PermissionError):
    """Fail-closed denial before any model endpoint is contacted."""


def load_policies(path: Path | None = None) -> dict[str, Any]:
    data = yaml.safe_load((path or POLICIES_PATH).read_text(encoding="utf-8"))
    plugins = {p["name"] for p in data.get("plugins", [])}
    required = {"oidc-auth", "rate-limiting", "pre-function"}
    missing = required - plugins
    if missing:
        raise ValueError(f"gateway policies missing required plugins: {missing}")
    oidc = next(p for p in data["plugins"] if p["name"] == "oidc-auth")
    if not oidc.get("config", {}).get("fail_closed", False):
        raise ValueError("oidc-auth must fail_closed")
    return data


def require_end_user_identity(headers: dict[str, str]) -> str:
    identity = headers.get("X-End-User-Identity") or headers.get("x-end-user-identity")
    if not identity:
        raise PermissionError("missing end-user identity — fail closed")
    return identity


def enforce_model_boundary(
    *,
    classification: str,
    egress_destination: str,
    approved_classifications: frozenset[str] | None = None,
    approved_egress: frozenset[str] | None = None,
) -> None:
    """G-012: deny over-class or non-approved egress before model call."""
    allowed_class = approved_classifications or APPROVED_CLASSIFICATIONS
    allowed_egress = approved_egress or DEFAULT_APPROVED_EGRESS
    if classification.upper() not in allowed_class:
        raise ModelBoundaryDenied(
            f"classification {classification} above approved handling level"
        )
    if egress_destination not in allowed_egress:
        raise ModelBoundaryDenied(
            f"egress destination not approved: {egress_destination}"
        )
