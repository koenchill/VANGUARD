#!/usr/bin/env bash
# Raw data ingest Local demo + integration gates (via .venv).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

FORCE=()
TESTS_ONLY=0
DEMO_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --force-venv) FORCE=(--force) ;;
    --tests-only) TESTS_ONLY=1 ;;
    --demo-only) DEMO_ONLY=1 ;;
  esac
done

PY="$(./scripts/ensure-venv.sh "${FORCE[@]}")"
failed=0

if [[ "$TESTS_ONLY" -eq 0 ]]; then
  echo "# raw-ingest: demo bulk + ongoing + quarantine"
  "$PY" tools/demo_raw_ingest.py || failed=1
fi

if [[ "$DEMO_ONLY" -eq 0 ]]; then
  echo "# raw-ingest: pytest tests/integration/test_enterprise_ingestion.py"
  "$PY" -m pytest tests/integration/test_enterprise_ingestion.py -v --tb=short || failed=1
fi

if [[ "$failed" -eq 0 ]]; then
  echo "# raw-ingest: PASS"
else
  echo "# raw-ingest: FAIL"
fi
exit "$failed"
