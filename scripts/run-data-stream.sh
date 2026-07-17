#!/usr/bin/env bash
# Stream live enterprise CDC-style events into Local Grafana.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

if ! docker ps --format '{{.Names}}' | grep -q '^vanguard-grafana-pg$'; then
  ./scripts/run-grafana-local.sh
fi

PY="$(./scripts/ensure-venv.sh)"
echo "# data-stream: http://127.0.0.1:33000/d/live_enterprise_stream"
echo "# data-stream: Ctrl+C to stop"
exec "$PY" tools/stream_local_source.py "$@"
