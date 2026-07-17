# analytics/grafana/local/

**Local Mission BI UI** — Grafana + Postgres mart stand-in. No cloud, no Trino cluster.

## Start

```powershell
.\scripts\run-grafana-local.ps1
```

- URL: http://127.0.0.1:33000  
- Login: `admin` / `vanguard`  
- Folder: **Mission BI**

Fresh DB seed (after changing SQL):

```powershell
.\scripts\run-grafana-local.ps1 -Rebuild
```

Stop:

```powershell
.\scripts\run-grafana-local.ps1 -Down
```

## What you get

| Piece | Role |
|-------|------|
| Postgres `:15432` | `mission_marts.reporting.*` time-series stand-in for Trino marts |
| Grafana `:33000` | Renders the four Mission BI dashboards with real graphs |
| Seed | Generated from `bi_metrics.yaml` + last `ingest-to-grafana` report snapshot |

Assurance: **G-001 Local portfolio UI** — not Cloud-Integration Trino/oauthPassThru.
