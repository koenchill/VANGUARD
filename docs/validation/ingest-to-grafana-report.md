# Ingest → Grafana Local Report

Generated: `2026-07-17T00:19:05.472108+00:00`

**Overall:** PASS — G-001 portfolio Local ingest→Grafana contract — not Cloud-Integration / not ATO

| Step | Result | Detail |
|------|--------|--------|
| `raw_enterprise_ingest` | PASS | enterprise-raw-001 |
| `curate_and_promote` | PASS | curated-enterprise-raw-001 |
| `mart_projection_fct_curation_health` | PASS | mission_marts.reporting.fct_curation_health |
| `grafana_mission_bi_contract` | PASS | 4 dashboards → MissionBI-Trino |
| `grafana_rls_simulated_view` | PASS | alpha=2 bravo=1 |

## Re-run

```powershell
.\scripts\run-ingest-to-grafana.ps1
```

Live Trino/Grafana in-cluster queries remain **Cloud-Integration** evidence.
