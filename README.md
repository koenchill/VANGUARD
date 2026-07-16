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

Application, infrastructure, security, tests, and docs live under dedicated top-level folders (`app/`, `infra/`, `security/`, `tests/`, `docs/`, `analytics/`, `backup-dr/`). **Do not place application source or Terraform at the repo root.**

## Current build phase

**Phase 10 — Security artifacts** (complete on `dev`): 10 STRIDE worksheets with DFDs, ATT&CK/ATLAS playbooks (incl. AML.M0015 + AML.T0043), OPA Trino RLS, Kyverno deny privileged/root, G-012 model-boundary ADR, NIST AI RMF GRC + audit schema.

Next: **Phase 11** — CI/CD + supply chain (SHA-pinned Actions, SBOM/cosign, real DAST).

## Quick facts

- **Sole query engine:** Trino (+ OPA for RLS)
- **tfvars only in:** `infra/terraform/app/` (`dev.tfvars.json` / `prod.tfvars.json`)
- **PowerBI gateway:** Windows Server EC2 cluster — never a container
