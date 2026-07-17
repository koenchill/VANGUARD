#!/usr/bin/env bash
# Local SQL optimization lab.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

if ! docker ps --format '{{.Names}}' | grep -q '^vanguard-grafana-pg$'; then
  echo "# sql-optimize: starting Local Grafana/Postgres first"
  ./scripts/run-grafana-local.sh
fi

PY="$(./scripts/ensure-venv.sh)"
echo "# sql-optimize: EXPLAIN ANALYZE lab on reporting.metric_series"
"$PY" tools/run_sql_optimization.py
echo "# sql-optimize: see docs/validation/sql-optimization-report.md"
