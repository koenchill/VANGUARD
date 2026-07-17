#!/usr/bin/env bash
# Ensure repo-local .venv exists; prints absolute path to venv python.
# Usage: PY=$(./scripts/ensure-venv.sh); "$PY" -m pytest ...

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if command -v python3.11 >/dev/null 2>&1; then
  BOOTSTRAP=python3.11
elif command -v python3 >/dev/null 2>&1; then
  BOOTSTRAP=python3
else
  BOOTSTRAP=python
fi

"$BOOTSTRAP" tools/ensure_venv.py "$@" >/dev/null
PY="$ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "Expected venv python missing: $PY" >&2
  exit 1
fi
printf '%s\n' "$PY"
