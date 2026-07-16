# VANGUARD

Forward-deployed agentic AI platform — **portfolio reference architecture** demonstrating enterprise data onboarding, curation at scale, multi-agent orchestration, dual-path BI, and AI security/GRC patterns for a GovCloud-style mission tenant.

> **Assurance boundary (G-001):** This is not an accredited production system. Nothing in this repository is ATO evidence.

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Stable baseline — phase gates passed |
| `dev` | Active Section 16 phase implementation |

## Repository root (kept minimal)

| Path | Role |
|------|------|
| `LICENSE` | Project license |
| `README.md` | This entrypoint |
| `AGENTS.md` | Coding-agent constraints and branching guide |
| `.cursorrules` | Same constraints for Cursor-compatible tools |
| `.cursor/rules/` | Always-on Cursor project rules |
| `.gitignore` | Ignore patterns for TF state, secrets, caches |
| `tools/` | Repo build tooling (resource-contract renderer) — not app code |

Application, infrastructure, security, tests, and docs live under dedicated top-level folders (`app/`, `infra/`, `security/`, `tests/`, `docs/`, `analytics/`, `backup-dr/`, `scripts/`). **Do not place application source or Terraform at the repo root.**

## Current build phase

**Phase 14 — Full validation** (complete on `main` / `dev`): Section 14 Local walkthrough all PASS; deliverables checklist evidence-linked; gap register reconciled (Phase 2 Local closed; Phase 3 Cloud / Phase 4 org remain open); Go for portfolio freeze / No-Go for ATO.

Build phases **0–14 complete**. See `docs/validation/go-no-go.md`.

## Mimic production locally

Portfolio Local evidence that approximates CI + a live gateway (not a tenant ATO drill):

```powershell
.\scripts\mimic-prod.ps1 -Quick
```

```bash
./scripts/mimic-prod.sh --quick
```

Details: `scripts/README.md`. Report: `docs/validation/mimic-prod-report.md`. Prefer Python **3.11** (CI version).

## Quick facts

- **Sole query engine:** Trino (+ OPA for RLS)
- **tfvars only in:** `infra/terraform/app/` (`dev.tfvars.json` / `prod.tfvars.json`)
- **PowerBI gateway:** Windows Server EC2 cluster — never a container
