#!/usr/bin/env bash
# Local Grafana Mission BI (no cloud).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE="analytics/grafana/local/docker-compose.yaml"

if [[ "${1:-}" == "--down" ]]; then
  docker compose -f "$COMPOSE" down -v
  echo "# grafana-local: stopped"
  exit 0
fi

FORCE=()
REBUILD=0
for arg in "$@"; do
  case "$arg" in
    --force-venv) FORCE=(--force) ;;
    --rebuild) REBUILD=1 ;;
  esac
done

command -v docker >/dev/null || { echo "Docker required"; exit 1; }
PY="$(./scripts/ensure-venv.sh "${FORCE[@]}")"
export PYTHONPATH="$ROOT"

echo "# grafana-local: refresh Local ingest->Grafana evidence"
"$PY" tools/demo_ingest_to_grafana.py >/dev/null || true

echo "# grafana-local: prepare seed + dashboards"
"$PY" tools/prepare_grafana_local.py

if [[ "$REBUILD" -eq 1 ]]; then
  docker compose -f "$COMPOSE" down -v
fi

echo "# grafana-local: starting Grafana on http://127.0.0.1:33000"
docker compose -f "$COMPOSE" up -d

for i in $(seq 1 40); do
  if curl -sf http://127.0.0.1:33000/api/health >/dev/null; then
    echo "# grafana-local: READY"
    echo "#   URL:      http://127.0.0.1:33000"
    echo "#   User:     admin"
    echo "#   Password: vanguard"
    exit 0
  fi
  sleep 2
done
docker compose -f "$COMPOSE" logs --tail 80
exit 1
