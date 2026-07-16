"""AI Gateway policy loader — Kong declarative / Mosaic-compatible."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

POLICIES_PATH = Path(__file__).with_name("policies.yaml")


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
