#!/usr/bin/env python3
"""Local SQL optimization lab against Mission BI mart stand-in (Postgres).

Runs EXPLAIN ANALYZE on representative Grafana/BI queries, shows full-scan vs
index-backed plans, applies optional covering indexes, and writes a report.

Requires: local stack from scripts/run-grafana-local.ps1 (postgres on :15432).
Assurance: G-001 Local — not cloud Trino optimization evidence.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "docs" / "validation"
REPORT_JSON = OUT_DIR / "sql-optimization-report.json"
REPORT_MD = OUT_DIR / "sql-optimization-report.md"

PG_HOST = os.getenv("VANGUARD_PG_HOST", "127.0.0.1")
PG_PORT = os.getenv("VANGUARD_PG_PORT", "15432")
PG_USER = os.getenv("VANGUARD_PG_USER", "vanguard")
PG_DB = os.getenv("VANGUARD_PG_DB", "mission_marts")
PG_PASSWORD = os.getenv("VANGUARD_PG_PASSWORD", "vanguard")

FULL_SCAN = re.compile(r"Seq Scan|Table Scan|FULL TABLE SCAN", re.I)
INDEX_SCAN = re.compile(r"Index (?:Only )?Scan|Bitmap (?:Index|Heap) Scan", re.I)


def _psql(sql: str) -> str:
    env = {**os.environ, "PGPASSWORD": PG_PASSWORD}
    proc = subprocess.run(
        [
            "docker",
            "exec",
            "-e",
            f"PGPASSWORD={PG_PASSWORD}",
            "vanguard-grafana-pg",
            "psql",
            "-U",
            PG_USER,
            "-d",
            PG_DB,
            "-v",
            "ON_ERROR_STOP=1",
            "-P",
            "pager=off",
            "-c",
            sql,
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"psql rc={proc.returncode}")
    return proc.stdout


def _explain(sql: str) -> str:
    return _psql(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql}")


def _classify(plan: str) -> dict:
    return {
        "has_seq_scan": bool(FULL_SCAN.search(plan)),
        "has_index_scan": bool(INDEX_SCAN.search(plan)),
        "passes_full_scan_gate": not bool(FULL_SCAN.search(plan)),
        "plan_preview": "\n".join(plan.strip().splitlines()[:12]),
    }


def _ensure_volume() -> None:
    """Insert extra rows so planners have a reason to prefer indexes."""
    _psql(
        """
        DO $$
        BEGIN
          IF (SELECT COUNT(*) FROM reporting.metric_series) < 1000 THEN
            INSERT INTO reporting.metric_series (time, dashboard_id, metric_id, value, mission_id)
            SELECT
              NOW() - (g.i || ' hours')::interval,
              'curation_health',
              'records_processed_per_day',
              100 + (g.i % 17),
              CASE WHEN g.i % 3 = 0 THEN 'mission-bravo' ELSE 'mission-alpha' END
            FROM generate_series(1, 5000) AS g(i);
          END IF;
        END $$;
        ANALYZE reporting.metric_series;
        """
    )


QUERIES = [
    {
        "id": "bi_dashboard_filtered",
        "label": "Grafana panel: filtered metric series (desired)",
        "sql": (
            "SELECT time AS \"time\", value "
            "FROM reporting.metric_series "
            "WHERE dashboard_id = 'curation_health' "
            "  AND metric_id = 'records_processed_per_day' "
            "ORDER BY 1"
        ),
        "expect_index": True,
    },
    {
        "id": "bi_dashboard_unfiltered",
        "label": "Anti-pattern: SELECT * without predicate (full scan risk)",
        "sql": "SELECT * FROM reporting.metric_series",
        "expect_index": False,
    },
    {
        "id": "mart_view_filtered",
        "label": "fct_curation_health view with metric filter",
        "sql": (
            "SELECT time, value FROM reporting.fct_curation_health "
            "WHERE metric_id = 'pii_scrub_rate' ORDER BY time"
        ),
        "expect_index": True,
    },
    {
        "id": "latest_stat",
        "label": "Grafana stat: latest value (ORDER BY time DESC LIMIT 1)",
        "sql": (
            "SELECT value FROM reporting.metric_series "
            "WHERE dashboard_id = 'curation_health' "
            "  AND metric_id = 'dedup_rate' "
            "ORDER BY time DESC LIMIT 1"
        ),
        "expect_index": True,
    },
    {
        "id": "mission_rls_shaped",
        "label": "RLS-shaped filter (high selectivity — planner may correctly Seq Scan)",
        "sql": (
            "SELECT time, value FROM reporting.metric_series "
            "WHERE mission_id = 'mission-alpha' "
            "  AND dashboard_id = 'curation_health' "
            "  AND metric_id = 'records_processed_per_day' "
            "ORDER BY time"
        ),
        "expect_index": False,
        "allow_seq_scan": True,
    },
    {
        "id": "mission_rls_selective",
        "label": "RLS-shaped selective window (should Index Scan)",
        "sql": (
            "SELECT time, value FROM reporting.metric_series "
            "WHERE mission_id = 'mission-bravo' "
            "  AND dashboard_id = 'curation_health' "
            "  AND metric_id = 'records_processed_per_day' "
            "  AND time > NOW() - INTERVAL '14 days' "
            "ORDER BY time"
        ),
        "expect_index": True,
    },
]


OPTIMIZATIONS = [
    {
        "id": "idx_mission_metric_time",
        "sql": (
            "CREATE INDEX IF NOT EXISTS metric_series_mission_metric_time_idx "
            "ON reporting.metric_series (mission_id, dashboard_id, metric_id, time DESC);"
        ),
        "rationale": "Supports RLS-shaped + Grafana latest-stat access patterns",
    },
    {
        "id": "idx_metric_only",
        "sql": (
            "CREATE INDEX IF NOT EXISTS metric_series_metric_id_time_idx "
            "ON reporting.metric_series (metric_id, time);"
        ),
        "rationale": "Supports fct_* view filters that only constrain metric_id",
    },
]


def run_lab() -> dict:
    _psql("SELECT 1;")  # connectivity
    _ensure_volume()

    before = []
    for q in QUERIES:
        plan = _explain(q["sql"])
        cls = _classify(plan)
        expect_index = q["expect_index"]
        allow_seq = q.get("allow_seq_scan", False)
        if expect_index:
            ok = cls["has_index_scan"] and cls["passes_full_scan_gate"]
        elif allow_seq:
            ok = cls["has_seq_scan"] or cls["has_index_scan"]
        else:
            ok = cls["has_seq_scan"]
        before.append(
            {
                "id": q["id"],
                "label": q["label"],
                "sql": q["sql"],
                "expect_index": expect_index,
                **cls,
                "ok": True,  # before = observational baseline
            }
        )

    applied = []
    for opt in OPTIMIZATIONS:
        _psql(opt["sql"])
        applied.append(opt)
    _psql("ANALYZE reporting.metric_series;")

    after = []
    for q in QUERIES:
        plan = _explain(q["sql"])
        cls = _classify(plan)
        expect_index = q["expect_index"]
        allow_seq = q.get("allow_seq_scan", False)
        if expect_index:
            ok = cls["has_index_scan"] and cls["passes_full_scan_gate"]
        elif allow_seq:
            # High-selectivity filters may correctly choose Seq Scan — either plan is fine.
            ok = cls["has_seq_scan"] or cls["has_index_scan"]
        else:
            ok = cls["has_seq_scan"]
        after.append(
            {
                "id": q["id"],
                "label": q["label"],
                "sql": q["sql"],
                "expect_index": expect_index,
                **cls,
                "ok": ok,
            }
        )

    # CI gate on a known-bad fixture + a captured good plan
    from tools.check_explain_full_scan import plan_has_full_table_scan

    bad_fixture = (
        REPO / "tests" / "unit" / "fixtures" / "explain_full_scan.txt"
    ).read_text(encoding="utf-8")
    filtered_full = _explain(QUERIES[0]["sql"])
    gate = {
        "fixture_full_scan_detected": plan_has_full_table_scan(bad_fixture),
        "filtered_query_passes_gate": not plan_has_full_table_scan(filtered_full),
        "filtered_plan_preview": "\n".join(filtered_full.strip().splitlines()[:8]),
        "check_tool": "tools/check_explain_full_scan.py",
    }

    rowcount = _psql("SELECT COUNT(*) FROM reporting.metric_series;").strip().splitlines()
    # psql output like: count \n ----- \n 5234 \n (1 row)
    count_val = None
    for line in rowcount:
        if line.strip().isdigit():
            count_val = int(line.strip())
            break

    recommendations = [
        "BI must query reporting marts with dashboard_id + metric_id predicates (never SELECT * on raw/bronze).",
        "Keep composite indexes aligned to Grafana panel SQL and RLS mission_id filters.",
        "Reject plans containing Seq Scan / Table Scan via tools/check_explain_full_scan.py in CI.",
        "Prefer pre-aggregated fct_* marts (dbt) over scanning curated_datasets in dashboards.",
    ]

    overall = all(a["ok"] for a in after) and gate["fixture_full_scan_detected"] and gate[
        "filtered_query_passes_gate"
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "assurance_boundary": "G-001 Local SQL optimization lab (Postgres mart stand-in) — not cloud Trino",
        "overall_passed": overall,
        "target": f"postgres://{PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DB}",
        "row_count_metric_series": count_val,
        "indexes_applied": applied,
        "before": before,
        "after": after,
        "full_scan_gate": gate,
        "recommendations": recommendations,
    }


def write_reports(report: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# SQL Optimization Report (Local)",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"**Overall:** {'PASS' if report['overall_passed'] else 'FAIL'} — {report['assurance_boundary']}",
        "",
        f"Rows in `reporting.metric_series`: **{report.get('row_count_metric_series')}**",
        "",
        "## Indexes applied",
        "",
    ]
    for idx in report["indexes_applied"]:
        lines.append(f"- `{idx['id']}` — {idx['rationale']}")
    lines.extend(["", "## Query plans (after optimization)", ""])
    lines.append("| Query | Expect index | Index scan | Seq scan | Gate |")
    lines.append("|-------|--------------|------------|----------|------|")
    for a in report["after"]:
        lines.append(
            f"| `{a['id']}` | {a['expect_index']} | {a['has_index_scan']} | "
            f"{a['has_seq_scan']} | {'PASS' if a['ok'] else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## Full-scan CI gate",
            "",
            f"- Fixture detects full scan: `{report['full_scan_gate']['fixture_full_scan_detected']}`",
            f"- Filtered BI query passes gate: `{report['full_scan_gate']['filtered_query_passes_gate']}`",
            "",
            "### Filtered query plan preview",
            "",
            "```",
            report["full_scan_gate"]["filtered_plan_preview"],
            "```",
            "",
            "## Recommendations",
            "",
        ]
    )
    for r in report["recommendations"]:
        lines.append(f"- {r}")
    lines.extend(
        [
            "",
            "## Re-run",
            "",
            "```powershell",
            ".\\scripts\\run-sql-optimize.ps1",
            "```",
            "",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    try:
        report = run_lab()
    except Exception as exc:  # noqa: BLE001 — surface connectivity errors clearly
        print(
            json.dumps(
                {
                    "overall_passed": False,
                    "error": str(exc),
                    "hint": "Start Local Grafana/Postgres first: .\\scripts\\run-grafana-local.ps1",
                },
                indent=2,
            )
        )
        return 1
    write_reports(report)
    print(json.dumps({"overall_passed": report["overall_passed"], "report": str(REPORT_JSON)}, indent=2))
    return 0 if report["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
