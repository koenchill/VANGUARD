# Mimic-Prod Report (Local)

Generated: `2026-07-17T00:40:48.094328+00:00`
Code: `2f9c71f`

**Overall:** PASS — Local evidence only (G-001).

| Stage | Result | Detail |
|-------|--------|--------|
| `deps` | SKIP | --skip-deps |
| `pyramid-core` | PASS | 85 passed in 13.79s |
| `gateway` | PASS | image=local/vanguard-gateway:mimic-prod probes ok on :18010 |
| `security` | PASS | cicd_gates rc=0; dast_localhost rc=0; live_headers=ok |
| `load` | SKIP | --skip-k6 |
| `resilience` | SKIP | --skip-resilience |
| `prod-sim` | SKIP | --skip-prod-sim |
| `walkthrough` | SKIP | --skip-walkthrough |

## How to re-run

```bash
./scripts/ensure-venv.sh   # or .\scripts\ensure-venv.ps1
./scripts/mimic-prod.sh
```
