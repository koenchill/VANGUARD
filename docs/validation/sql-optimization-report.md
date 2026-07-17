# SQL Optimization Report (Local)

Generated: `2026-07-17T00:41:47.935512+00:00`

**Overall:** PASS — G-001 Local SQL optimization lab (Postgres mart stand-in) — not cloud Trino

Rows in `reporting.metric_series`: **5480**

## Indexes applied

- `idx_mission_metric_time` — Supports RLS-shaped + Grafana latest-stat access patterns
- `idx_metric_only` — Supports fct_* view filters that only constrain metric_id

## Query plans (after optimization)

| Query | Expect index | Index scan | Seq scan | Gate |
|-------|--------------|------------|----------|------|
| `bi_dashboard_filtered` | True | True | False | PASS |
| `bi_dashboard_hot_metric` | False | False | True | PASS |
| `bi_dashboard_unfiltered` | False | False | True | PASS |
| `mart_view_filtered` | True | True | False | PASS |
| `latest_stat` | True | True | False | PASS |
| `mission_rls_shaped` | False | False | True | PASS |
| `mission_rls_selective` | True | True | False | PASS |

## Full-scan CI gate

- Fixture detects full scan: `True`
- Filtered BI query passes gate: `True`

### Filtered query plan preview

```
QUERY PLAN                                                                          
--------------------------------------------------------------------------------------------------------------------------------------------------------------
 Sort  (cost=67.60..67.69 rows=35 width=16) (actual time=0.113..0.117 rows=37 loops=1)
   Sort Key: "time"
   Sort Method: quicksort  Memory: 26kB
   Buffers: shared hit=10
   ->  Bitmap Heap Scan on metric_series  (cost=4.64..66.70 rows=35 width=16) (actual time=0.035..0.057 rows=37 loops=1)
         Recheck Cond: ((dashboard_id = 'curation_health'::text) AND (metric_id = 'pii_scrub_rate'::text))
```

## Recommendations

- BI must query reporting marts with dashboard_id + metric_id predicates (never SELECT * on raw/bronze).
- Keep composite indexes aligned to Grafana panel SQL and RLS mission_id filters.
- Reject plans containing Seq Scan / Table Scan via tools/check_explain_full_scan.py in CI.
- Prefer pre-aggregated fct_* marts (dbt) over scanning curated_datasets in dashboards.

## Re-run

```powershell
.\scripts\run-sql-optimize.ps1
```
