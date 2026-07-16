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

PY="$(./scripts/ensure-venv.sh "${FORCE[@]}")"
echo "VANGUARD smoke → $PY tools/run_mimic_prod.py …"
exec "$PY" tools/run_mimic_prod.py \
  --skip-deps --skip-k6 --skip-resilience --skip-prod-sim --skip-walkthrough \
  "${KEEP[@]}"
