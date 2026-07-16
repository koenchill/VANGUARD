"""Local evaluator mirroring security/k8s-container-hardening/opa-trino-rls.rego."""

from __future__ import annotations

from typing import Any

CLASS_RANK = {"U": 0, "FOUO": 1, "SECRET": 2, "TS": 3}


def evaluate_trino_rls(inp: dict[str, Any]) -> dict[str, Any]:
    user = inp.get("user") or {}
    name = user.get("name") or ""
    classification = user.get("classification")
    mission_ids = user.get("mission_ids") or []
    if not name or not classification or not mission_ids:
        return {"allow": False, "deny_reason": "missing_or_unmapped_end_user_identity"}

    if inp.get("action") != "SelectFromColumns":
        return {"allow": False, "deny_reason": "unsupported_action"}
    table = inp.get("table") or {}
    if table.get("catalog") != "mission_marts" or table.get("schema") != "reporting":
        return {"allow": False, "deny_reason": "table_not_in_marts"}

    resource = inp.get("resource") or {}
    if resource.get("mission_id") not in mission_ids:
        return {"allow": False, "deny_reason": "row_not_permitted_for_principal"}
    if CLASS_RANK.get(classification, -1) < CLASS_RANK.get(resource.get("classification", "TS"), 99):
        return {"allow": False, "deny_reason": "row_not_permitted_for_principal"}
    return {"allow": True, "deny_reason": None}
