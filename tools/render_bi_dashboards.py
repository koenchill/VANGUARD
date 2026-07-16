"""Build Grafana + PowerBI dashboard definitions from analytics/bi_metrics.yaml."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
METRICS = REPO / "analytics" / "bi_metrics.yaml"


def load_catalog() -> dict:
    return yaml.safe_load(METRICS.read_text(encoding="utf-8"))


def grafana_dashboard(dash: dict) -> dict:
    panels = []
    for i, metric in enumerate(dash["metrics"], start=1):
        panels.append(
            {
                "id": i,
                "type": "timeseries" if "trend" in metric["id"] or "rate" in metric["id"] else "stat",
                "title": metric["label"],
                "gridPos": {"h": 8, "w": 12, "x": (i - 1) % 2 * 12, "y": ((i - 1) // 2) * 8},
                "datasource": {"type": "grafana-trino-datasource", "uid": "MissionBI-Trino"},
                "targets": [
                    {
                        "refId": "A",
                        "rawSql": (
                            f"SELECT * FROM {dash['trino_relation']} "
                            f"/* metric:{metric['id']} */"
                        ),
                        "format": "table",
                    }
                ],
            }
        )
    return {
        "uid": dash["id"],
        "title": dash["title"],
        "tags": ["mission-bi", "vanguard", dash["id"]],
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 1,
        "refresh": "1h",
        "panels": panels,
        "templating": {"list": []},
        "annotations": {"list": []},
        "editable": False,
    }


def powerbi_definition(dash: dict) -> dict:
    """Source-controlled .pbix.json — Portable DirectQuery report definition (G-003 path)."""
    return {
        "format": "vanguard.pbix.json/v1",
        "name": dash["id"],
        "displayName": dash["title"],
        "connectionMode": "DirectQuery",
        "forbidImportMode": True,
        "gatewayCluster": "vanguard-mission-gateway",
        "identity": "kerberos_constrained_delegation",
        "datasource": {
            "engine": "trino",
            "catalog": "mission_marts",
            "schema": "reporting",
            "relation": dash["trino_relation"].split(".")[-1],
        },
        "pages": [
            {
                "name": "Overview",
                "visuals": [
                    {
                        "id": m["id"],
                        "title": m["label"],
                        "type": "card" if "funnel" not in m["id"] else "funnel",
                        "queryMetric": m["id"],
                    }
                    for m in dash["metrics"]
                ],
            }
        ],
        "rls": {
            "enforcedAt": "trino_opa",
            "defenseInDepth": "powerbi_native_rls",
        },
    }


def render_all() -> list[Path]:
    catalog = load_catalog()
    written: list[Path] = []
    for dash in catalog["dashboards"]:
        g_path = REPO / dash["path_grafana"]
        p_path = REPO / dash["path_powerbi"]
        g_path.parent.mkdir(parents=True, exist_ok=True)
        p_path.parent.mkdir(parents=True, exist_ok=True)
        g_path.write_text(json.dumps(grafana_dashboard(dash), indent=2) + "\n", encoding="utf-8")
        p_path.write_text(json.dumps(powerbi_definition(dash), indent=2) + "\n", encoding="utf-8")
        written.extend([g_path, p_path])
    return written


def main() -> None:
    paths = render_all()
    for p in paths:
        print(p.relative_to(REPO))


if __name__ == "__main__":
    main()
