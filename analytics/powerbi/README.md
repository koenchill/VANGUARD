# analytics/powerbi/

PowerBI **DirectQuery** report definitions (`*.pbix.json`) for the hybrid path via the
Windows Server gateway cluster (G-003). Same metrics as `analytics/grafana/dashboards/`
— regenerated from `analytics/bi_metrics.yaml` via `tools/render_bi_dashboards.py`.

Binary `.pbix` packages for a live tenant are published from these definitions through
Power BI Desktop / ALM; Import mode is forbidden (`forbidImportMode: true`).
