#!/usr/bin/env python3
"""Local E2E: raw enterprise ingest → promote → Grafana Mission BI contract.

Demonstrates the data-engineering path without live Trino/Grafana servers:
  1. Bulk raw landing + checksum gate
  2. Stage + atomic promote (G-014) so a version is queryable
  3. Project curation-health mart rows from pipeline state
  4. Assert Grafana dashboards bind MissionBI-Trino to reporting marts
  5. Simulate dashboard RLS view for two analysts

Assurance (G-001): Local / portfolio evidence — not Cloud-Integration or ATO.
Live panel queries against cluster Trino remain a Cloud gap.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from analytics.rls import (  # noqa: E402
    ANALYST_ALPHA,
    ANALYST_BRAVO,
    MartRow,
    filter_rows_for_principal,
    row_counts_for_two_identities,
)
from app.data_pipelines.db.models import CurationStage  # noqa: E402
from app.data_pipelines.db.session import create_db_engine, init_schema, session_factory  # noqa: E402
from app.data_pipelines.ingestion.bulk import run_bulk_onboarding  # noqa: E402
from app.data_pipelines.ingestion.types import LANDING_PREFIX, TransferPath  # noqa: E402
from app.data_pipelines.ingestion.validation import InMemoryObjectStore  # noqa: E402
from app.data_pipelines.promotion import (  # noqa: E402
    PromotionArtifacts,
    get_active_version,
    promote,
    resolve_queryable_version,
    stage_candidate,
)

OUT_DIR = REPO / "docs" / "validation"
REPORT_JSON = OUT_DIR / "ingest-to-grafana-report.json"
REPORT_MD = OUT_DIR / "ingest-to-grafana-report.md"
METRICS = REPO / "analytics" / "bi_metrics.yaml"
DATASOURCES = REPO / "analytics" / "grafana" / "provisioning" / "datasources.yaml"


def _step(name: str, ok: bool, **detail) -> dict:
    return {"id": name, "ok": ok, **detail}


def step_raw_ingest(session, store: InMemoryObjectStore) -> tuple[dict, list]:
    files = {
        "mission_alpha/events.parquet": b"enterprise-raw-batch-001-aaaa",
        "mission_alpha/assets.parquet": b"enterprise-raw-batch-001-bbbb",
        "mission_alpha/telemetry.json": b'{"records":120,"source":"enterprise"}',
    }
    batch, records = run_bulk_onboarding(
        session,
        store,
        batch_id="enterprise-raw-001",
        source_uri="s3://enterprise-source/mission-alpha",
        source_files=files,
    )
    landing = [o.key for o in store.list_prefix(f"{LANDING_PREFIX}enterprise-raw-001/")]
    ok = (
        batch.path == TransferPath.BULK
        and len(records) == 3
        and all(r.curation_stage == CurationStage.landed for r in records)
        and len(landing) == 3
    )
    return (
        _step(
            "raw_enterprise_ingest",
            ok,
            batch_id=batch.batch_id,
            path=batch.path.value,
            landed_count=len(records),
            dataset_versions=[r.dataset_version for r in records],
            landing_keys=landing,
            stages=[r.curation_stage.value for r in records],
        ),
        records,
    )


def step_promote(session, landed_records: list) -> dict:
    # Promote a curated candidate derived from the landed enterprise batch.
    parent = landed_records[0]
    version = "curated-enterprise-raw-001"
    artifacts = PromotionArtifacts(
        dataset_version=version,
        source_uri=parent.source_uri,
        lakefs_commit_id="lakefs-enterprise-raw-001",
        vector_snapshot_id="vec-enterprise-raw-001",
        model_prompt_digest="digest-enterprise-raw-001",
        quality_score=0.96,
        lineage_parent_id=parent.id,
    )
    stage_candidate(session, artifacts)
    previous = promote(session, version)
    active = get_active_version(session)
    queryable = resolve_queryable_version(session, version)
    ok = active == version and queryable == version
    return _step(
        "curate_and_promote",
        ok,
        previous_active=previous or None,
        active_dataset_version=active,
        queryable_version=queryable,
        lineage_parent=parent.dataset_version,
        quality_score=artifacts.quality_score,
    )


def step_mart_projection(landed_count: int, active_version: str | None) -> tuple[dict, list[MartRow]]:
    """Local stand-in for mission_marts.reporting.fct_curation_health rows."""
    rows = [
        MartRow(
            dataset_version=active_version or "none",
            mission_id="mission-alpha",
            classification="FOUO",
            quality_score=0.96,
        ),
        MartRow(
            dataset_version=f"landed-batch-n{landed_count}",
            mission_id="mission-alpha",
            classification="U",
            quality_score=0.91,
        ),
        MartRow(
            dataset_version="other-mission-secret",
            mission_id="mission-bravo",
            classification="SECRET",
            quality_score=0.88,
        ),
    ]
    funnel = {
        "raw_landed": landed_count,
        "approved_active": 1 if active_version else 0,
        "rejected_quarantine": 0,
    }
    ok = landed_count > 0 and active_version is not None
    return (
        _step(
            "mart_projection_fct_curation_health",
            ok,
            trino_relation="mission_marts.reporting.fct_curation_health",
            funnel=funnel,
            row_count=len(rows),
            note="Local projection — not a live Trino query",
        ),
        rows,
    )


def step_grafana_contract() -> dict:
    catalog = yaml.safe_load(METRICS.read_text(encoding="utf-8"))
    datasources = yaml.safe_load(DATASOURCES.read_text(encoding="utf-8"))
    trino = next(d for d in datasources["datasources"] if d["name"] == "MissionBI-Trino")
    ds_ok = (
        trino["jsonData"].get("oauthPassThru") is True
        and trino["jsonData"].get("catalog") == "mission_marts"
    )

    dashboards = []
    all_ok = ds_ok
    for dash in catalog["dashboards"]:
        path = REPO / dash["path_grafana"]
        doc = json.loads(path.read_text(encoding="utf-8"))
        relation = dash["trino_relation"]
        panels = doc.get("panels", [])
        panel_titles = {p["title"] for p in panels}
        expected = {m["label"] for m in dash["metrics"]}
        ds_uids = {p.get("datasource", {}).get("uid") for p in panels}
        sqls = [
            t.get("rawSql", "")
            for p in panels
            for t in p.get("targets", [])
        ]
        relation_ok = all(relation in sql for sql in sqls) and len(sqls) == len(panels)
        metrics_ok = panel_titles == expected
        uid_ok = ds_uids == {"MissionBI-Trino"}
        ok = path.is_file() and relation_ok and metrics_ok and uid_ok
        all_ok = all_ok and ok
        dashboards.append(
            {
                "id": dash["id"],
                "title": dash["title"],
                "ok": ok,
                "path": dash["path_grafana"],
                "trino_relation": relation,
                "panel_count": len(panels),
                "datasource_uids": sorted(ds_uids),
                "metrics_match_catalog": metrics_ok,
                "sql_binds_mart": relation_ok,
            }
        )

    never_query = catalog.get("connection", {}).get("never_query", [])
    return _step(
        "grafana_mission_bi_contract",
        all_ok,
        missionbi_trino={
            "oauthPassThru": trino["jsonData"].get("oauthPassThru"),
            "catalog": trino["jsonData"].get("catalog"),
            "ok": ds_ok,
        },
        never_query_raw_zones=never_query,
        dashboards=dashboards,
    )


def step_dashboard_rls_view(rows: list[MartRow]) -> dict:
    alpha = filter_rows_for_principal(rows, ANALYST_ALPHA)
    bravo = filter_rows_for_principal(rows, ANALYST_BRAVO)
    denied = filter_rows_for_principal(rows, None)
    a_count, b_count = row_counts_for_two_identities(rows, ANALYST_ALPHA, ANALYST_BRAVO)
    ok = a_count != b_count and a_count > 0 and b_count > 0 and denied == []
    return _step(
        "grafana_rls_simulated_view",
        ok,
        analyst_alpha={
            "name": ANALYST_ALPHA.name,
            "rows_visible": a_count,
            "dataset_versions": [r.dataset_version for r in alpha],
        },
        analyst_bravo={
            "name": ANALYST_BRAVO.name,
            "rows_visible": b_count,
            "dataset_versions": [r.dataset_version for r in bravo],
        },
        fail_closed_without_identity=len(denied) == 0,
        note="Simulates oauthPassThru → OPA/Trino RLS; not a live Grafana session",
    )


def write_reports(report: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Ingest → Grafana Local Report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"**Overall:** {'PASS' if report['overall_passed'] else 'FAIL'} — {report['assurance_boundary']}",
        "",
        "| Step | Result | Detail |",
        "|------|--------|--------|",
    ]
    for s in report["steps"]:
        mark = "PASS" if s["ok"] else "FAIL"
        detail = s.get("batch_id") or s.get("active_dataset_version") or s.get("trino_relation") or ""
        if s["id"] == "grafana_mission_bi_contract":
            detail = f"{len(s.get('dashboards', []))} dashboards → MissionBI-Trino"
        if s["id"] == "grafana_rls_simulated_view":
            detail = (
                f"alpha={s['analyst_alpha']['rows_visible']} "
                f"bravo={s['analyst_bravo']['rows_visible']}"
            )
        lines.append(f"| `{s['id']}` | {mark} | {detail} |")
    lines.extend(
        [
            "",
            "## Re-run",
            "",
            "```powershell",
            ".\\scripts\\run-ingest-to-grafana.ps1",
            "```",
            "",
            "Live Trino/Grafana in-cluster queries remain **Cloud-Integration** evidence.",
            "",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    engine = create_db_engine("sqlite+pysqlite:///:memory:")
    init_schema(engine)
    Session = session_factory(engine)
    store = InMemoryObjectStore()
    steps: list[dict] = []

    with Session() as session:
        ingest_step, landed = step_raw_ingest(session, store)
        steps.append(ingest_step)
        promo_step = step_promote(session, landed)
        steps.append(promo_step)
        active = promo_step.get("active_dataset_version")
        mart_step, rows = step_mart_projection(ingest_step["landed_count"], active)
        steps.append(mart_step)
        steps.append(step_grafana_contract())
        steps.append(step_dashboard_rls_view(rows))

    overall = all(s["ok"] for s in steps)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "assurance_boundary": "G-001 portfolio Local ingest→Grafana contract — not Cloud-Integration / not ATO",
        "overall_passed": overall,
        "pipeline": [
            "raw enterprise files",
            "landing/raw + checksum gate",
            "curation metadata (landed)",
            "stage_candidate + promote (active)",
            "mart projection fct_curation_health",
            "Grafana MissionBI-Trino dashboard contract",
            "RLS-simulated dashboard view",
        ],
        "steps": steps,
        "reports": {
            "json": str(REPORT_JSON.relative_to(REPO)),
            "md": str(REPORT_MD.relative_to(REPO)),
        },
    }
    write_reports(report)
    print(json.dumps({"overall_passed": overall, "report": str(REPORT_JSON)}, indent=2))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
