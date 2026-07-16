# scripts/

Operator entrypoints for **Local / portfolio** production-mimicry (G-001).
These do **not** claim Cloud-Integration or ATO readiness.

| Script | Purpose |
|--------|---------|
| `mimic-prod.ps1` / `mimic-prod.sh` | Full Local mimic: deps → CI pytest gates → live gateway smoke → security → optional k6 → chaos/audit/eval → prod-sim → Section 14 report |
| (underlying) `tools/run_mimic_prod.py` | Cross-platform orchestrator used by both wrappers |

## Prerequisites

- Python 3.11+ with `pip`
- Docker (for live gateway smoke; omit with `-SkipGateway` / `--skip-gateway`)
- Optional: [k6](https://k6.io) for live load (omit with `-SkipK6` / `--skip-k6`)

## Quick start (Windows)

```powershell
.\scripts\mimic-prod.ps1 -Quick
```

## Quick start (Linux/macOS)

```bash
chmod +x scripts/mimic-prod.sh
./scripts/mimic-prod.sh --quick
```

## Full pyramid without containers

```powershell
.\scripts\mimic-prod.ps1 -SkipGateway -SkipK6
```

## Keep gateway up for manual probing

```powershell
.\scripts\mimic-prod.ps1 -Quick -KeepGateway
curl http://127.0.0.1:8000/readyz
```

Reports land in `docs/validation/mimic-prod-report.{json,md}`.

For CI-parity only (no Docker):

```bash
pip install -r tests/requirements.txt
python -m pytest tests/unit tests/integration -q
```

For the documented Section 14 Local freeze walkthrough alone:

```bash
python tools/run_section14_walkthrough.py
```
