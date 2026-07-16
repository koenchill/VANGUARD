# AGENTS.md — VANGUARD Coding Agent Guide

Portfolio reference architecture for a forward-deployed, high-assurance agentic AI platform (AWS GovCloud pattern). **Not an accredited production system** — no claim here is ATO evidence (G-001).

This file mirrors `.cursorrules` and `.cursor/rules/` so any coding agent has the same hard constraints.

## Hard rules (do not violate)

1. **`app/`** never contains Terraform, Dockerfiles, or Kubernetes manifests.
2. **`infra/terraform/modules/`** contains zero hardcoded environment values.
3. **`infra/terraform/app/`** contains **ONLY** `dev.tfvars.json` and `prod.tfvars.json` — no `.tf` files ever.
4. **Technology baseline is fixed:** Delta Lake, Ray, lakeFS, Milvus, Trino (sole query engine), PowerBI standard gateway on Windows Server (never a container), ArgoCD, Semgrep, K6. Do not substitute without explicit baseline change.
5. **Dockerfiles** install into `/opt/venv`, never `--user` / root-owned paths — runtime UID is non-root (`8888`).
6. **Karpenter** uses `karpenter.sh/v1` only; never mix GPU and CPU-optimized families in one NodePool.
7. **Before creating a file**, grep for existing references — existing interfaces are authoritative.
8. **When a task cites Section N** of the build prompt, read that section before implementing.
9. **Keep the repo root minimal** — no application or infra source files at root.
10. **`app/api/`** follows MVC-equivalent: thin routers (controller), services/agents (logic), models/schemas + data layer (model). Views live in `analytics/` (PowerBI / Grafana).

## Branching

| Branch | Role |
|--------|------|
| `main` | Stable / gate-passed integrations only |
| `dev` | Active implementation of build phases |

Complete each Section 16 phase on `dev`, pass its gate, then merge to `main` when the phase gate is green.

## Where config lives

| Path | Allowed contents |
|------|------------------|
| `infra/terraform/app/` | `dev.tfvars.json`, `prod.tfvars.json` **only** |
| `infra/terraform/modules/` | Reusable modules — variables, no env literals |
| `infra/terraform/environments/{dev,prod}/` | Module wiring (`main.tf`, `variables.tf`, `outputs.tf`, `providers.tf`) — no tfvars |
| `app/` | Application code only |
| `infra/docker/`, `infra/k8s/` | Container and GitOps manifests |
| `security/` | STRIDE, ATLAS, hardening, GRC |
| Repo root | `README.md`, `LICENSE`, `AGENTS.md`, `.cursorrules`, `.gitignore`, `.cursor/` |

## Build order

Follow Section 16 phases **0 → 14** in order. Do not skip ahead or fabricate stand-ins for missing dependencies.

## Quick answers agents must know

- **Where do tfvars live?** `infra/terraform/app/` — and **nothing else** is allowed there (no `.tf` files).
- **Sole query engine?** Trino (with OPA sidecar for RLS).
- **PowerBI gateway?** Windows Server EC2 cluster — not Kubernetes.
