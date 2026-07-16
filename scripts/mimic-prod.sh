#!/usr/bin/env bash
# Mimic production-like Local evidence for VANGUARD (G-001 portfolio — not ATO).
#
# Usage:
#   ./scripts/mimic-prod.sh
#   ./scripts/mimic-prod.sh --quick
#   ./scripts/mimic-prod.sh --skip-gateway --skip-k6

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

echo "VANGUARD mimic-prod → python tools/run_mimic_prod.py $*"
exec python tools/run_mimic_prod.py "$@"
