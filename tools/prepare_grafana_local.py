#!/usr/bin/env python3
"""Prepare Local Grafana stack: seed SQL + Postgres-backed Mission BI dashboards.

Does not require cloud Trino. Run then:
  docker compose -f analytics/grafana/local/docker-compose.yaml up -d
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
LOCAL = REPO / "analytics" / "grafana" / "local"
INIT = LOCAL / "init"
DASH_OUT = LOCAL / "dashboards"
DS_OUT = LOCAL / "provisioning" / "datasources"
DB_PROV = LOCAL / "provisioning" / "dashboards"
METRICS = REPO / "analytics" / "bi_metrics.yaml"
SOURCE_DASH = REPO / "analytics" / "grafana" / "dashboards"
INGEST_REPORT = REPO / "docs" / "validation" / "ingest-to-grafana-report.json"

DS_UID = "MissionBI-Local"


def _series(days: int = 14, base: float = 100.0, noise: float = 8.0, trend: float = 1.5) -> list[tuple[datetime, float]]:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    rng = random.Random(42)
    out: list[tuple[datetime, float]] = []
    for i in range(days, -1, -1):
        ts = now - timedelta(days=i)
        value = base + trend * (days - i) + rng.uniform(-noise, noise)
        out.append((ts, round(max(0.0, value), 2)))
    return out


def write_seed_sql() -> Path:
    INIT.mkdir(parents=True, exist_ok=True)
    # Enrich from last Local ingest→Grafana run when present.
    landed = 3
    active = "curated-enterprise-raw-001"
    if INGEST_REPORT.is_file():
        report = json.loads(INGEST_REPORT.read_text(encoding="utf-8"))
        for step in report.get("steps", []):
            if step.get("id") == "raw_enterprise_ingest":
                landed = int(step.get("landed_count") or landed)
            if step.get("id") == "curate_and_promote" and step.get("active_dataset_version"):
                active = step["active_dataset_version"]

    catalog = yaml.safe_load(METRICS.read_text(encoding="utf-8"))
    lines = [
        "-- Local Mission BI mart stand-in (Postgres). Replaces Trino mission_marts for Local UI.",
        "CREATE SCHEMA IF NOT EXISTS reporting;",
        "",
        "DROP TABLE IF EXISTS reporting.metric_series;",
        "DROP TABLE IF EXISTS reporting.pipeline_snapshot;",
        "",
        """CREATE TABLE reporting.pipeline_snapshot (
  captured_at timestamptz NOT NULL,
  active_dataset_version text NOT NULL,
  raw_landed_count int NOT NULL,
  curation_stage text NOT NULL
);""",
        f"INSERT INTO reporting.pipeline_snapshot VALUES (NOW(), '{active}', {landed}, 'active');",
        "",
        """CREATE TABLE reporting.metric_series (
  time timestamptz NOT NULL,
  dashboard_id text NOT NULL,
  metric_id text NOT NULL,
  value double precision NOT NULL,
  mission_id text NOT NULL DEFAULT 'mission-alpha'
);""",
        "CREATE INDEX ON reporting.metric_series (dashboard_id, metric_id, time);",
        "CREATE INDEX IF NOT EXISTS metric_series_mission_metric_time_idx "
        "ON reporting.metric_series (mission_id, dashboard_id, metric_id, time DESC);",
        "CREATE INDEX IF NOT EXISTS metric_series_metric_id_time_idx "
        "ON reporting.metric_series (metric_id, time);",
        "",
    ]

    # Deterministic series per metric in the BI catalog.
    bases = {
        "records_processed_per_day": (120.0 + landed * 10, 10.0, 2.0),
        "pii_scrub_rate": (0.92, 0.02, 0.001),
        "dedup_rate": (0.15, 0.02, 0.0),
        "hitl_approval_throughput": (18.0, 3.0, 0.2),
        "curation_stage_funnel": (float(landed), 0.5, 0.1),
        "quality_score_trend": (0.91, 0.02, 0.002),
        "drift_flag_rate": (0.04, 0.01, 0.0),
        "drift_by_source_uri": (3.0, 1.0, 0.0),
        "sast_sca_dast_pass_rate": (0.97, 0.01, 0.0),
        "stride_residual_risk": (2.0, 0.3, 0.0),
        "nist_ai_rmf_coverage": (78.0, 2.0, 0.4),
        "backup_dr_restore_pass_rate": (1.0, 0.0, 0.0),
        "task_completion_rate": (0.88, 0.03, 0.002),
        "faithfulness_score": (0.9, 0.02, 0.001),
        "cost_per_inference": (0.012, 0.002, 0.0),
        "mission_scenario_outcomes": (7.0, 1.0, 0.1),
        "per_agent_step_telemetry": (240.0, 20.0, 3.0),
    }

    for dash in catalog["dashboards"]:
        dash_id = dash["id"]
        for metric in dash["metrics"]:
            mid = metric["id"]
            base, noise, trend = bases.get(mid, (50.0, 5.0, 0.5))
            # Rates stay 0-1-ish when base < 2
            for ts, value in _series(14, base=base, noise=noise, trend=trend):
                if base <= 1.5:
                    value = min(1.0, max(0.0, value))
                lines.append(
                    "INSERT INTO reporting.metric_series "
                    f"(time, dashboard_id, metric_id, value, mission_id) VALUES "
                    f"('{ts.isoformat()}', '{dash_id}', '{mid}', {value}, 'mission-alpha');"
                )

    # Convenience views matching Trino relation names (Local alias).
    for dash in catalog["dashboards"]:
        rel = dash["trino_relation"].split(".")[-1]  # fct_*
        lines.append(
            f"CREATE OR REPLACE VIEW reporting.{rel} AS "
            f"SELECT time, metric_id, value, mission_id "
            f"FROM reporting.metric_series WHERE dashboard_id = '{dash['id']}';"
        )

    path = INIT / "01_seed_marts.sql"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_datasource() -> Path:
    DS_OUT.mkdir(parents=True, exist_ok=True)
    doc = {
        "apiVersion": 1,
        "datasources": [
            {
                "name": "MissionBI-Local",
                "uid": DS_UID,
                "type": "postgres",
                "access": "proxy",
                "url": "postgres:5432",
                "user": "vanguard",
                "secureJsonData": {"password": "vanguard"},
                "jsonData": {
                    "database": "mission_marts",
                    "sslmode": "disable",
                    "postgresVersion": 1600,
                    "timescaledb": False,
                },
                "isDefault": True,
                "editable": False,
            }
        ],
    }
    path = DS_OUT / "datasources.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return path


def write_dashboard_provider() -> Path:
    DB_PROV.mkdir(parents=True, exist_ok=True)
    doc = {
        "apiVersion": 1,
        "providers": [
            {
                "name": "mission-bi-local",
                "orgId": 1,
                "folder": "Mission BI",
                "folderUid": "mission-bi",
                "type": "file",
                "disableDeletion": False,
                "updateIntervalSeconds": 10,
                "options": {"path": "/var/lib/grafana/dashboards/mission-bi"},
            }
        ],
    }
    path = DB_PROV / "dashboards.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return path


def _panel_sql(dashboard_id: str, metric_id: str, panel_type: str) -> str:
    if panel_type == "timeseries":
        return (
            "SELECT time AS \"time\", value "
            "FROM reporting.metric_series "
            f"WHERE dashboard_id = '{dashboard_id}' AND metric_id = '{metric_id}' "
            "ORDER BY 1"
        )
    # stat / table / default
    return (
        "SELECT value "
        "FROM reporting.metric_series "
        f"WHERE dashboard_id = '{dashboard_id}' AND metric_id = '{metric_id}' "
        "ORDER BY time DESC LIMIT 1"
    )


def write_local_dashboards() -> list[Path]:
    DASH_OUT.mkdir(parents=True, exist_ok=True)
    catalog = yaml.safe_load(METRICS.read_text(encoding="utf-8"))
    written: list[Path] = []
    for dash in catalog["dashboards"]:
        src = REPO / dash["path_grafana"]
        doc = json.loads(src.read_text(encoding="utf-8"))
        metric_by_label = {m["label"]: m["id"] for m in dash["metrics"]}
        for panel in doc.get("panels", []):
            panel["datasource"] = {"type": "postgres", "uid": DS_UID}
            label = panel.get("title", "")
            metric_id = metric_by_label.get(label)
            if not metric_id:
                # fallback: keep first metric
                metric_id = dash["metrics"][0]["id"]
            raw_sql = _panel_sql(dash["id"], metric_id, panel.get("type", "stat"))
            panel["targets"] = [
                {
                    "refId": "A",
                    "datasource": {"type": "postgres", "uid": DS_UID},
                    "format": "time_series" if panel.get("type") == "timeseries" else "table",
                    "rawSql": raw_sql,
                    "rawQuery": True,
                }
            ]
            if panel.get("type") == "timeseries":
                panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
                panel["fieldConfig"]["defaults"]["custom"] = {
                    "drawStyle": "line",
                    "lineWidth": 2,
                    "fillOpacity": 15,
                    "showPoints": "auto",
                }
        doc["tags"] = list(dict.fromkeys([*(doc.get("tags") or []), "local", "no-cloud"]))
        doc["refresh"] = "30s"
        doc["title"] = f"{doc.get('title', dash['title'])} (Local)"
        out = DASH_OUT / src.name
        out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        written.append(out)
    return written


def main() -> int:
    seed = write_seed_sql()
    ds = write_datasource()
    prov = write_dashboard_provider()
    dashes = write_local_dashboards()
    print(
        json.dumps(
            {
                "ok": True,
                "seed": str(seed.relative_to(REPO)),
                "datasource": str(ds.relative_to(REPO)),
                "provider": str(prov.relative_to(REPO)),
                "dashboards": [str(p.relative_to(REPO)) for p in dashes],
                "ui": "http://127.0.0.1:33000",
                "login": {"user": "admin", "password": "vanguard"},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
