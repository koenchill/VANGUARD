# NIST AI RMF Mapping — VANGUARD GRC Policies

Assurance boundary (G-001): portfolio reference policies — not ATO evidence.

## GOVERN

| Function | Control in this build | Artifact |
|----------|----------------------|----------|
| GOVERN 1.1 / 1.2 | Roles & structural separation app/infra/security | `AGENTS.md`, repo tree |
| GOVERN 1.4 | Risk acceptance tracked in gap register | Section 15 (program) |
| GOVERN 4.1 | Risk tolerance for autonomous action | G-013 HITL gate |
| GOVERN 6.1 | Supply chain governance | G-019 pinned Actions (Phase 11) |

## MAP

| Function | Control in this build | Artifact |
|----------|----------------------|----------|
| MAP 2.x | Per-component risk categorization | `security/stride/*.md` |
| MAP 3.x | Threat techniques mapped | `security/mitre-attack/` |

## MEASURE

| Function | Control in this build | Artifact |
|----------|----------------------|----------|
| MEASURE 2.7 | Safety/control metrics | G-013 suite; BI security dashboard |
| MEASURE 2.11 | Access/fairness controls tested | `analytics/rls/`; OPA Trino RLS |

## MANAGE

| Function | Control in this build | Artifact |
|----------|----------------------|----------|
| MANAGE 2.2 / 2.3 | Supply chain + incident response | Playbooks; Semgrep/Trivy/DAST |
| MANAGE 4.1 / 4.2 | Human oversight | `human_in_the_loop.py` |

Compliance posture metrics feed `analytics` security & compliance dashboard
(`fct_security_compliance` mart).
