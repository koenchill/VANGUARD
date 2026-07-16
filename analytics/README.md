# analytics/

BI layer — deliberately NOT under `app/`; consumed, not owned, by the agentic
application. Dual-path: PowerBI (hybrid/GovCloud via Windows gateway) and Grafana
(air-gapped/IL, same hardened instance as infra monitoring).

| Artifact | Role |
|----------|------|
| `bi_metrics.yaml` | SSOT for the four minimum dashboards |
| `grafana/` | Datasources (`oauthPassThru`) + JSON dashboards |
| `powerbi/` | DirectQuery report definitions (`*.pbix.json`) |
| `rls/` | Build-side Trino/OPA RLS simulation (§14 Phase 6) |
