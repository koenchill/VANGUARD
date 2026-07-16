#!/usr/bin/env bash
# Live gateway smoke via repo .venv.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

FORCE=()
KEEP=()
for arg in "$@"; do
  case "$arg" in
    --force-venv) FORCE=(--force) ;;
    --keep-gateway) KEEP=(--keep-gateway) ;;
  esac
done

if [[ -z "${VANGUARD_GATEWAY_PORT:-}" ]]; then
  if command -v ss >/dev/null 2>&1 && ss -ltn | grep -q ':8000 '; then
    export VANGUARD_GATEWAY_PORT=18010
    echo "Host :8000 is busy; using VANGUARD_GATEWAY_PORT=$VANGUARD_GATEWAY_PORT for smoke"
  else
    export VANGUARD_GATEWAY_PORT=8000
  fi
fi

PY="$(./scripts/ensure-venv.sh "${FORCE[@]}")"
echo "VANGUARD smoke -> $PY tools/run_mimic_prod.py … (port $VANGUARD_GATEWAY_PORT)"
exec "$PY" tools/run_mimic_prod.py \
  --skip-deps --skip-k6 --skip-resilience --skip-prod-sim --skip-walkthrough \
  "${KEEP[@]}"
