"""Phase 8 — dual-path BI dashboards, identity forwarding, and RLS gate."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from analytics.rls import (
    ANALYST_ALPHA,
    ANALYST_BRAVO,
    filter_rows_for_principal,
    row_counts_for_two_identities,
    sample_mart_rows,
)

REPO = Path(__file__).resolve().parents[2]
METRICS = REPO / "analytics" / "bi_metrics.yaml"
DATASOURCES = REPO / "analytics" / "grafana" / "provisioning" / "datasources.yaml"
ANSIBLE_ROOT = REPO / "infra" / "ansible" / "powerbi-gateway"
DSC = ANSIBLE_ROOT / "dsc" / "PowerBIGateway.ps1"


def test_four_dashboards_exist_on_both_paths() -> None:
    catalog = yaml.safe_load(METRICS.read_text(encoding="utf-8"))
    assert len(catalog["dashboards"]) == 4
    for dash in catalog["dashboards"]:
        g = REPO / dash["path_grafana"]
        p = REPO / dash["path_powerbi"]
        assert g.is_file(), g
        assert p.is_file(), p
        g_doc = json.loads(g.read_text(encoding="utf-8"))
        p_doc = json.loads(p.read_text(encoding="utf-8"))
        g_metrics = {panel["title"] for panel in g_doc["panels"]}
        p_metrics = {v["title"] for v in p_doc["pages"][0]["visuals"]}
        expected = {m["label"] for m in dash["metrics"]}
        assert g_metrics == expected
        assert p_metrics == expected
        assert p_doc["connectionMode"] == "DirectQuery"
        assert p_doc["forbidImportMode"] is True


def test_grafana_oauth_passthru_and_prometheus_retained() -> None:
    data = yaml.safe_load(DATASOURCES.read_text(encoding="utf-8"))
    names = {d["name"] for d in data["datasources"]}
    assert names >= {"Prometheus", "MissionBI-Trino", "MissionBI-MetadataDB"}
    trino = next(d for d in data["datasources"] if d["name"] == "MissionBI-Trino")
    assert trino["jsonData"]["oauthPassThru"] is True
    assert trino["jsonData"]["catalog"] == "mission_marts"


def test_grafana_folder_providers_separate_mission_and_infra() -> None:
    prov = yaml.safe_load(
        (REPO / "analytics" / "grafana" / "provisioning" / "dashboards.yaml").read_text(
            encoding="utf-8"
        )
    )
    folders = {p["folder"] for p in prov["providers"]}
    assert folders == {"Mission BI", "Infra Monitoring"}


def test_rls_two_identities_different_row_counts() -> None:
    rows = sample_mart_rows()
    a, b = row_counts_for_two_identities(rows, ANALYST_ALPHA, ANALYST_BRAVO)
    assert a != b
    assert a > 0 and b > 0
    # Alpha FOUO on mission-alpha → U + FOUO only (2), not SECRET.
    assert a == 2
    # Bravo SECRET on bravo+charlie → bravo U/FOUO + charlie SECRET (3).
    assert b == 3


def test_rls_fail_closed_without_identity() -> None:
    assert filter_rows_for_principal(sample_mart_rows(), None) == []


def test_gateway_ansible_and_dsc_artifacts_exist() -> None:
    assert (ANSIBLE_ROOT / "playbooks" / "install_gateway.yml").is_file()
    assert (ANSIBLE_ROOT / "playbooks" / "configure_kerberos_delegation.yml").is_file()
    assert (ANSIBLE_ROOT / "roles" / "powerbi_gateway" / "tasks" / "install.yml").is_file()
    assert (ANSIBLE_ROOT / "roles" / "powerbi_gateway" / "tasks" / "kerberos.yml").is_file()
    text = DSC.read_text(encoding="utf-8")
    assert "Configuration PowerBIGateway" in text
    assert "Kerberos" in text or "delegation" in text.lower()


def test_no_powerbi_in_k8s() -> None:
    for path in (REPO / "infra" / "k8s").rglob("*.yaml"):
        assert "powerbi" not in path.read_text(encoding="utf-8").lower(), path


def test_identity_mechanisms_documented_in_catalog() -> None:
    catalog = yaml.safe_load(METRICS.read_text(encoding="utf-8"))
    assert catalog["identity"]["powerbi"] == "kerberos_constrained_delegation"
    assert catalog["identity"]["grafana"] == "oauthPassThru"
    assert catalog["identity"]["fail_closed"] is True
