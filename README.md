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

Application, infrastructure, security, tests, and docs are added in later phases under their dedicated top-level folders (`app/`, `infra/`, `security/`, `tests/`, `docs/`, `analytics/`, `backup-dr/`). **Do not place source or Terraform at the repo root.**

## Current build phase

**Phase 1 — Repository scaffolding** (complete on `dev`): Section 1 directory tree with folder READMEs only — no Terraform, Dockerfiles, or application code yet.

Next: **Phase 2** — Docker images and the resource-contract renderer (G-007, G-008).

## Quick facts

- **Sole query engine:** Trino (+ OPA for RLS)
- **tfvars only in:** `infra/terraform/app/` (`dev.tfvars.json` / `prod.tfvars.json`)
- **PowerBI gateway:** Windows Server EC2 cluster — never a container
