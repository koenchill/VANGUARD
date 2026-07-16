# app/telemetry/

Per-agent-step event logging into the curation metadata DB (`TelemetryEvent`); events
are modeled into `sql/marts/reporting/` for BI — dashboards never read raw logs.
