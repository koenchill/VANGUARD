# scripts/

Operator entrypoints for **Local / portfolio** production-mimicry (G-001).
These do **not** claim Cloud-Integration or ATO readiness.

All runners **create/use repo-local `.venv`** first (prefer Python **3.11**, already gitignored).

| Script | Purpose |
|--------|---------|
| `ensure-venv.ps1` / `ensure-venv.sh` | Create `.venv` + `pip install -r tests/requirements.txt` |
| `run-smoke.ps1` / `run-smoke.sh` | `.venv` → unit/integration → live gateway smoke |
| `run-prod-simulation.ps1` / `run-prod-simulation.sh` | `.venv` → `tests/production-simulation` |
| `mimic-prod.ps1` / `mimic-prod.sh` | Full Local mimic (includes smoke + prod-sim) |
| (underlying) `tools/ensure_venv.py` / `tools/run_mimic_prod.py` | Cross-platform implementations |

## Prerequisites

- Python **3.11+** (`py -3.11` on Windows recommended)
- Docker (for live gateway smoke; omit with `-SkipGateway` / `--skip-gateway`)
- Optional: [k6](https://k6.io) for live load

## Bootstrap venv only

```powershell
.\scripts\ensure-venv.ps1
.\.venv\Scripts\python.exe -c "import sys; print(sys.prefix)"
```

```bash
./scripts/ensure-venv.sh
.venv/bin/python -c "import sys; print(sys.prefix)"
```

## Smoke (gateway)

```powershell
.\scripts\run-smoke.ps1
.\scripts\run-smoke.ps1 -KeepGateway
```

## Production simulation

```powershell
.\scripts\run-prod-simulation.ps1
```

## Full mimic-prod

```powershell
.\scripts\mimic-prod.ps1 -Quick
```

```bash
chmod +x scripts/*.sh
./scripts/mimic-prod.sh --quick
```

Reports: `docs/validation/mimic-prod-report.{json,md}`.

Recreate a clean venv:

```powershell
.\scripts\ensure-venv.ps1 -Force
```
