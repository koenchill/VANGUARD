#!/usr/bin/env bash
# Production-simulation (mission-alpha) via repo .venv.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

FORCE=()
for arg in "$@"; do
  if [[ "$arg" == "--force-venv" ]]; then FORCE=(--force); fi
done

PY="$(./scripts/ensure-venv.sh "${FORCE[@]}")"
echo "VANGUARD prod-simulation → $PY -m pytest tests/production-simulation -v --tb=short"
exec "$PY" -m pytest tests/production-simulation -v --tb=short
