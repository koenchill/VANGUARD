#!/usr/bin/env bash
# Mimic production-like Local evidence for VANGUARD (G-001 portfolio — not ATO).
# Always bootstraps repo .venv first (Python 3.11+).
#
# Usage:
#   ./scripts/mimic-prod.sh
#   ./scripts/mimic-prod.sh --quick
#   ./scripts/mimic-prod.sh --skip-gateway --skip-k6

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

FORCE=()
PASSTHRU=()
for arg in "$@"; do
  if [[ "$arg" == "--force-venv" ]]; then
    FORCE=(--force)
  else
    PASSTHRU+=("$arg")
  fi
done

PY="$(./scripts/ensure-venv.sh "${FORCE[@]}")"
echo "# mimic-prod: $PY tools/run_mimic_prod.py --skip-deps ${PASSTHRU[*]}"
exec "$PY" tools/run_mimic_prod.py --skip-deps "${PASSTHRU[@]}"
