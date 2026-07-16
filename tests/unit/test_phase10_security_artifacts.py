"""Phase 10 — STRIDE/MITRE/OPA/Kyverno/G-012 artifact gates."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
STRIDE = REPO / "security" / "stride"
HARDENING = REPO / "security" / "k8s-container-hardening"
PLAYBOOKS = REPO / "security" / "playbooks" / "ai-incident-response"
ADR = REPO / "docs" / "adrs" / "model-boundary.md"

EXPECTED_STRIDE = [
    "01-ai-gateway.md",
    "02-orchestration.md",
    "03-rag-pipeline.md",
    "04-tool-use.md",
    "05-data-curation.md",
    "06-enterprise-ingestion.md",
    "07-bi-reporting.md",
    "08-k8s-karpenter.md",
    "09-cicd-pipeline.md",
    "10-terraform-state.md",
]


def test_ten_stride_worksheets_have_dfd_and_residual() -> None:
    for name in EXPECTED_STRIDE:
        path = STRIDE / name
        assert path.is_file(), name
        text = path.read_text(encoding="utf-8")
        assert "```mermaid" in text
        assert "## Residual risk summary" in text
        assert "Spoofing" in text and "Elevation of Privilege" in text


def test_worked_example_playbooks_reference_real_resources() -> None:
    m0015 = (PLAYBOOKS / "aml-m0015-llm-prompt-injection.md").read_text(encoding="utf-8")
    t0043 = (PLAYBOOKS / "aml-t0043-analytical-trust.md").read_text(encoding="utf-8")
    assert "app/gateway" in m0015
    assert "agent-quarantine" in m0015
    assert "quality_score" in t0043
    assert "sql/marts/reporting" in t0043
    assert "active_dataset_pointer" in t0043 or "lineage" in t0043


def test_kyverno_forbids_privileged_and_root() -> None:
    docs = list(
        yaml.safe_load_all(
            (HARDENING / "kyverno-deny-privileged-root.yaml").read_text(encoding="utf-8")
        )
    )
    names = {d["metadata"]["name"] for d in docs if d}
    assert "forbid-privileged-pods" in names
    assert "forbid-root-containers" in names
    fixture = yaml.safe_load(
        (HARDENING / "fixtures" / "deliberately-privileged-pod.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert fixture["spec"]["containers"][0]["securityContext"]["privileged"] is True
    assert fixture["spec"]["containers"][0]["securityContext"]["runAsUser"] == 0


def test_opa_trino_rls_fail_closed_and_filters_rows() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "opa_eval", HARDENING / "opa_trino_rls_eval.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    denied = mod.evaluate_trino_rls({"user": {}, "action": "SelectFromColumns"})
    assert denied["allow"] is False

    allowed = mod.evaluate_trino_rls(
        {
            "user": {
                "name": "analyst.alpha",
                "classification": "FOUO",
                "mission_ids": ["mission-alpha"],
            },
            "action": "SelectFromColumns",
            "table": {"catalog": "mission_marts", "schema": "reporting"},
            "resource": {"mission_id": "mission-alpha", "classification": "U"},
        }
    )
    assert allowed["allow"] is True

    blocked = mod.evaluate_trino_rls(
        {
            "user": {
                "name": "analyst.alpha",
                "classification": "FOUO",
                "mission_ids": ["mission-alpha"],
            },
            "action": "SelectFromColumns",
            "table": {"catalog": "mission_marts", "schema": "reporting"},
            "resource": {"mission_id": "mission-alpha", "classification": "SECRET"},
        }
    )
    assert blocked["allow"] is False


def test_g012_adr_and_gateway_boundary_denies() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert "G-012" in text
    assert "Private connectivity" in text or "private" in text.lower()
    from app.gateway import enforce_model_boundary
    from app.gateway.gateway import ModelBoundaryDenied
    import pytest

    enforce_model_boundary(
        classification="FOUO",
        egress_destination="model.inference.vpc.internal",
    )
    with pytest.raises(ModelBoundaryDenied):
        enforce_model_boundary(
            classification="SECRET",
            egress_destination="model.inference.vpc.internal",
        )
    with pytest.raises(ModelBoundaryDenied):
        enforce_model_boundary(
            classification="U",
            egress_destination="public.openai.example",
        )


def test_audit_schema_covers_required_event_types() -> None:
    schema = json.loads((REPO / "security" / "grc" / "audit-schema.json").read_text())
    enums = schema["properties"]["event_type"]["enum"]
    for required in (
        "opa_decision",
        "g013_approval",
        "tool_call",
        "model_request",
        "data_version_ref",
        "admin_change",
    ):
        assert required in enums


def test_quarantine_networkpolicy_present() -> None:
    text = (REPO / "infra" / "k8s" / "base" / "networkpolicies.yaml").read_text(
        encoding="utf-8"
    )
    assert "name: agent-quarantine" in text
    assert "vanguard.io/quarantine" in text


def test_runtimeclasses_pin_sandbox_nodepool() -> None:
    docs = list(
        yaml.safe_load_all((HARDENING / "runtimeclass-sandbox.yaml").read_text())
    )
    for doc in docs:
        if not doc:
            continue
        assert doc["scheduling"]["nodeSelector"]["karpenter.sh/nodepool"] == "sandbox-runtime"
