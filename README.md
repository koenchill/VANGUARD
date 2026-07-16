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

**Phase 9 — Agentic app + HITL** (complete on `dev`): supervisor/tools, LangGraph-style COA graph, RAG+Milvus HNSW, Kong policies, telemetry, G-022 COA sim, and G-013 approval protocol (all attack suite cases fail closed).

Next: **Phase 10** — Security artifacts (STRIDE, MITRE/ATLAS, OPA/Kyverno, GRC).

## Quick facts

- **Sole query engine:** Trino (+ OPA for RLS)
- **tfvars only in:** `infra/terraform/app/` (`dev.tfvars.json` / `prod.tfvars.json`)
- **PowerBI gateway:** Windows Server EC2 cluster — never a container
