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

## Catalog pages (Playlists / Library / Snapshots / Public)

Empty Grafana catalog pages (dinosaur placeholders) can be filled with Local Mission BI content:

```powershell
.\scripts\seed-grafana-catalog.ps1
```

| Page | Seeded content |
|------|----------------|
| Playlists | **Mission BI — Local Freeze Rotation** (5 dashboards, 1m interval) |
| Library panels | Mart stats: curation throughput, quality score, stream events landed |
| Snapshots | Point-in-time snapshots of curation, quality, and live stream boards |
| Public dashboards | Public Local shares for the same three boards |

Assurance: G-001 Local only — not Cloud-Integration / not ATO.

## Live streaming (integrated-source assumption)

```powershell
.\scripts\run-data-stream.ps1
```

Opens **Live Enterprise Stream (Local)** and prints CDC events to the console while Grafana graphs update every 2s.
