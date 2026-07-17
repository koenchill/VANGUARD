#!/usr/bin/env bash
# Local E2E: raw enterprise ingest -> promote -> Grafana Mission BI contract.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

FORCE=()
WITH_PYTEST=0
for arg in "$@"; do
  case "$arg" in
    --force-venv) FORCE=(--force) ;;
    --with-pytest) WITH_PYTEST=1 ;;
  esac
done

PY="$(./scripts/ensure-venv.sh "${FORCE[@]}")"
failed=0

echo "# ingest-to-grafana: raw enterprise ingest through Grafana contract"
"$PY" tools/demo_ingest_to_grafana.py || failed=1

if [[ "$WITH_PYTEST" -eq 1 ]]; then
  echo "# ingest-to-grafana: related integration suites"
  "$PY" -m pytest \
    tests/integration/test_enterprise_ingestion.py \
    tests/integration/test_promotion_controller.py \
    tests/integration/test_bi_dual_path.py \
    -q --tb=line || failed=1
fi

if [[ "$failed" -eq 0 ]]; then
  echo "# ingest-to-grafana: PASS — docs/validation/ingest-to-grafana-report.md"
else
  echo "# ingest-to-grafana: FAIL"
fi
exit "$failed"
