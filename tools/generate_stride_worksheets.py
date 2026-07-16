"""Generate Phase 10 STRIDE worksheets (Section 10 component inventory)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "security" / "stride"

COMPONENTS = [
    {
        "id": "01-ai-gateway",
        "title": "AI Gateway",
        "code": ["app/gateway/gateway.py", "app/gateway/policies.yaml"],
        "dfd": """flowchart LR
  U[End User / Partner] --> GW[Kong AI Gateway app/gateway]
  GW -->|OIDC + rate limit + PII filter| ORCH[orchestration/graphs.py]
  GW -->|deny over-class / bad egress| X[Blocked G-012]
  GW -->|anomaly tokens| NP[NetworkPolicy quarantine]
  ORCH --> TEL[telemetry/events.py]""",
        "threats": {
            "S": "Forged service identity on gateway-agent channel",
            "T": "Prompt injection payloads mutating downstream tool args",
            "R": "Operator deletes gateway access logs after misuse",
            "I": "Response leaks higher-classification snippets",
            "D": "Recursive agent loops exhaust gateway workers",
            "E": "Plugin misconfig grants unauthenticated invoke",
        },
        "mitigations": {
            "S": "OIDC fail-closed; mTLS Gateway↔Agent (policies.yaml oidc-auth)",
            "T": "pre-function prompt filter; G-013 HITL for commit_recommendation",
            "R": "WORM audit stream (G-018); TelemetryEvent append-only path",
            "I": "classification gate enforce_model_boundary; Trino OPA RLS",
            "D": "Kong rate-limiting plugin (120/min); Karpenter HPA absorb",
            "E": "require X-End-User-Identity; deny missing identity",
        },
        "residual": "Shared plugin chain misconfiguration remains residual until Cloud-Integration plugin unit tests run against a live Kong DP.",
    },
    {
        "id": "02-orchestration",
        "title": "Orchestration layer",
        "code": ["app/orchestration/graphs.py", "app/agents/supervisor.py"],
        "dfd": """flowchart LR
  GW[AI Gateway] --> G[MissionGraph recon to commit]
  G --> SUP[Supervisor]
  SUP --> TOOLS[ScopedToolExecutor]
  SUP --> HITL[human_in_the_loop.py]
  SUP --> TEL[TelemetryLogger]""",
        "threats": {
            "S": "Step runs under wrong agent_id",
            "T": "Graph edge skipped to bypass HITL node",
            "R": "Step logs omitted for failed commits",
            "I": "Plan state leaks mission_id across tenants",
            "D": "Unbounded graph cycles",
            "E": "Non-HITL path invokes commit_recommendation",
        },
        "mitigations": {
            "S": "actor_id bound into G-013 digest",
            "T": "approve_commit node mandatory before commit edge",
            "R": "telemetry.log_step on every run_step",
            "I": "tenant + mission_id on GraphState; OPA RLS downstream",
            "D": "Fixed edge map; no cyclic edges in MissionGraph",
            "E": "ScopedToolExecutor requires ApprovalToken when requires_hitl",
        },
        "residual": "Graph runner is a LangGraph-equivalent; residual until compiled LangGraph checkpointing is Cloud-Integration proven.",
    },
    {
        "id": "03-rag-pipeline",
        "title": "RAG pipeline",
        "code": ["app/rag/ingestion.py", "app/rag/chunking.py", "app/rag/milvus_adapter.py"],
        "dfd": """flowchart LR
  CUR[Approved curated docs] --> ING[ingest_documents]
  ING -->|reject landed/raw| X[Denied]
  ING --> CHK[chunk_document]
  CHK --> MIL[MilvusAdapter HNSW M=16]
  MIL --> AGENT[RAG retrieve / query_mission_data]""",
        "threats": {
            "S": "Unapproved dataset_version presented as active",
            "T": "Poisoned chunks in vector index",
            "R": "Upsert without dataset_version attribution",
            "I": "Cross-mission vector recall",
            "D": "efSearch too high starves nodes",
            "E": "Landing-zone docs indexed",
        },
        "mitigations": {
            "S": "ActiveDatasetPointer (G-014) for consumer resolve",
            "T": "Only curation_stage approved|active accepted",
            "R": "Chunk carries dataset_version; telemetry on retrieve",
            "I": "Mission-scoped collections; Trino/OPA for mart joins",
            "D": "Explicit HnswParams; NodePool limits",
            "E": "ingest_documents raises on non-curated stages",
        },
        "residual": "Local Milvus stand-in; recall/latency vs golden set still Local evidence only.",
    },
    {
        "id": "04-tool-use",
        "title": "Tool-use layer",
        "code": ["app/agents/tools.py", "app/tools/manifests/", "app/rl_sim/coa_simulation.py"],
        "dfd": """flowchart LR
  SUP[Supervisor] --> EXE[ScopedToolExecutor]
  EXE --> MAN[ToolScopeManifest]
  EXE -->|requires_hitl| HITL[G-013 authorize_execution]
  EXE --> IMPL[tool implementations]
  RLSIM[rl_sim CoaSimulation] -.->|same interface sandboxed| MAN""",
        "threats": {
            "S": "Tool invoked with spoofed actor_id",
            "T": "Argument substitution after approval",
            "R": "Tool call without agent identity log",
            "I": "resource_scope broader than manifest",
            "D": "Parallel high-cost tool storms",
            "E": "Code-exec escapes to node",
        },
        "mitigations": {
            "S": "G-013 digest binds actor_id",
            "T": "Canonical digest over exact_arguments",
            "R": "TelemetryLogger + WORM (G-018)",
            "I": "allowed_resource_scopes enforced",
            "D": "max_concurrency on manifest; gateway rate limit",
            "E": "sandbox-runtime NodePool + Kyverno deny privileged",
        },
        "residual": "gVisor/Kata RuntimeClass declared; live escape tests are Cloud-Integration.",
    },
    {
        "id": "05-data-curation",
        "title": "Data curation pipeline (incl. metadata DB)",
        "code": [
            "app/data_pipelines/promotion/",
            "app/data_pipelines/db/models.py",
            "app/data_pipelines/sql/",
        ],
        "dfd": """flowchart LR
  LAND[landing/raw validated] --> CUR[dbt curation models]
  CUR --> META[(RDS metadata dataset_records)]
  CUR --> PROM[promotion controller G-014]
  PROM --> PTR[active_dataset_pointer]
  META --> MARTS[sql/marts/reporting]""",
        "threats": {
            "S": "Falsified hitl_approval_status",
            "T": "Poisoned quality_score / lineage (AML.T0043)",
            "R": "Curation run without lakefs_commit_id",
            "I": "Replica serves unapproved stage",
            "D": "Full-table scans on facts",
            "E": "Partial promote leaves orphan active",
        },
        "mitigations": {
            "S": "HITL status transitions audited",
            "T": "BI provenance panels; lineage reconcile playbook",
            "R": "lakeFS hooks; TelemetryEvent",
            "I": "BI reads marts + replica only",
            "D": "EXPLAIN CI gate; marts pre-aggregate",
            "E": "Atomic pointer flip; fault-injection tests",
        },
        "residual": "Analytical-trust detection is Design+Local; live dashboard anomaly wiring is Cloud-Integration.",
    },
    {
        "id": "06-enterprise-ingestion",
        "title": "Enterprise data ingestion / connectivity boundary",
        "code": [
            "app/data_pipelines/ingestion/",
            "infra/terraform/modules/data-transfer/",
        ],
        "dfd": """flowchart LR
  SRC[Enterprise source] -->|DataSync/Snowball OR CDC| LAND[landing/raw/batch_id]
  LAND --> VAL[validate_landing_batch]
  VAL -->|checksum fail| Q[landing/quarantine]
  VAL -->|ok| META[curation_stage=landed]
  VAL -->|deny| BZ[bronze/silver/gold blocked]""",
        "threats": {
            "S": "Rogue account assumes transfer role",
            "T": "Corrupted objects silently promoted",
            "R": "Transfer without batch audit",
            "I": "Transfer role writes curated zones",
            "D": "Unbounded bulk floods landing",
            "E": "Ongoing path reuses bulk credentials overly broad",
        },
        "mitigations": {
            "S": "Time-boxed read-only transfer IAM (tf module)",
            "T": "Checksum/count reconcile; quarantine",
            "R": "TransferBatch metadata + landed DatasetRecord",
            "I": "ObjectStore PermissionError on curated prefixes",
            "D": "Job windows; Karpenter pipeline-cpu limits",
            "E": "Separate bulk.py vs ongoing.py code paths",
        },
        "residual": "Live DataSync/Snowball cutover evidence remains Cloud-Integration (Section 15).",
    },
    {
        "id": "07-bi-reporting",
        "title": "BI / reporting layer",
        "code": [
            "analytics/bi_metrics.yaml",
            "analytics/grafana/",
            "analytics/powerbi/",
            "analytics/rls/",
        ],
        "dfd": """flowchart LR
  MARTS[Trino mission_marts.reporting] --> PBI[PowerBI via Windows gateway]
  MARTS --> GRAF[Grafana MissionBI-Trino oauthPassThru]
  META[(metadata replica)] --> GRAF
  PBI -->|Kerberos constrained delegation| TRINO[Trino+OPA]
  GRAF -->|Forward OAuth Identity| TRINO""",
        "threats": {
            "S": "Shared gateway service identity used for all viewers",
            "T": "Import-mode cache serves stale/poisoned mart",
            "R": "Dashboard edits without provenance",
            "I": "RLS bypass via native BI filters only",
            "D": "Heavy DirectQuery storms",
            "E": "PowerBI gateway as K8s workload",
        },
        "mitigations": {
            "S": "G-004 Kerberos / oauthPassThru to real user",
            "T": "forbidImportMode in pbix.json defs",
            "R": "bi_metrics.yaml SSOT; folder RBAC Mission vs Infra",
            "I": "OPA primary RLS; analytics/rls sim proves distinct counts",
            "D": "Marts only; rate limits at Trino",
            "E": "EC2 Windows cluster via ansible; no powerbi in k8s",
        },
        "residual": "Vendor-tenant failover and live dual-identity Trino audit proof is Cloud-Integration.",
    },
    {
        "id": "08-k8s-karpenter",
        "title": "K8s / Karpenter control plane",
        "code": [
            "infra/k8s/karpenter/nodepools.yaml",
            "infra/k8s/base/networkpolicies.yaml",
            "security/k8s-container-hardening/",
        ],
        "dfd": """flowchart LR
  DEP[Deployments from resource contracts] --> NP[Exclusive NodePools]
  DEP --> NET[NetworkPolicy default-deny]
  NET -->|incident| QUAR[quarantine isolation]
  KY[Kyverno/OPA] -->|deny privileged/root| DEP""",
        "threats": {
            "S": "Pod scheduled onto wrong NodePool",
            "T": "Privileged pod escapes to node",
            "R": "Admission decisions not logged",
            "I": "Cross-namespace east-west access",
            "D": "Mixed GPU/CPU pool waste / starvation",
            "E": "sandbox workload on gateway-general",
        },
        "mitigations": {
            "S": "nodeSelector + taints per workload-tier (G-016)",
            "T": "Kyverno forbid privileged/root; RuntimeClass gVisor/Kata",
            "R": "Admission controller audit to G-018",
            "I": "default-deny NetworkPolicies per namespace",
            "D": "Mutually exclusive instance families",
            "E": "sandbox-runtime exclusive pool + tolerations",
        },
        "residual": "Policy dry-run vs live API server rejection is Cloud-Integration.",
    },
    {
        "id": "09-cicd-pipeline",
        "title": "CI/CD pipeline",
        "code": ["security/sast-sca-dast/", ".github/workflows/ (Phase 11)"],
        "dfd": """flowchart LR
  PR[Pull Request] --> SAST[Semgrep]
  PR --> SCA[Trivy]
  PR --> SBOM[syft + cosign]
  SAST --> DAST[Build gateway to /readyz to ZAP]
  DAST -->|block prod hostnames| OK[Merge gate]""",
        "threats": {
            "S": "Unpinned Action replaced with malicious tag",
            "T": "Poisoned dependency in lockfile",
            "R": "Failed scan quietly continued",
            "I": "DAST hits production hostname",
            "D": "Runner DoS via malicious workflow",
            "E": "Privileged GITHUB_TOKEN overreach",
        },
        "mitigations": {
            "S": "SHA-pinned Actions (G-019) — Phase 11 YAML",
            "T": "SCA exit-code 1 on CRITICAL/HIGH",
            "R": "Jobs fail closed; required checks",
            "I": "Runner network policy hard-block prod hosts (G-015)",
            "D": "permissions contents:read default",
            "E": "Least-privilege job tokens",
        },
        "residual": "Full workflow YAML lands in Phase 11; this worksheet binds intended controls to the DAST design.",
    },
    {
        "id": "10-terraform-state",
        "title": "Terraform state / backend",
        "code": [
            "infra/terraform/environments/",
            "infra/terraform/backend-configs/",
            "infra/terraform/app/",
        ],
        "dfd": """flowchart LR
  DEV[environments/dev] --> S3D[S3 state + DynamoDB lock DEV]
  PROD[environments/prod] --> S3P[S3 state + DynamoDB lock PROD]
  APP[app/dev|prod.tfvars.json] --> DEV
  APP --> PROD
  CI[tflint/checkov] -->|deny .tf under app/| APP""",
        "threats": {
            "S": "Stolen CI role applies to wrong account",
            "T": "State file tampering / drift hide",
            "R": "Apply without recorded plan",
            "I": "Shared state across envs",
            "D": "State lock stuck blocking remediations",
            "E": "Hardcoded secrets in modules",
        },
        "mitigations": {
            "S": "Per-env backends; IAM boundary",
            "T": "DynamoDB lock; versioned S3 state",
            "R": "Plan artifacts retained in CI",
            "I": "Isolated state per environment (no shared file)",
            "D": "Lock timeout runbooks",
            "E": "Variable-only modules; app/ tfvars JSON only",
        },
        "residual": "Remote backend enablement against GovCloud tenant is Cloud-Integration.",
    },
]

LETTERS = [
    ("S", "Spoofing"),
    ("T", "Tampering"),
    ("R", "Repudiation"),
    ("I", "Information Disclosure"),
    ("D", "Denial of Service"),
    ("E", "Elevation of Privilege"),
]


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for c in COMPONENTS:
        lines = [
            f"# STRIDE Worksheet — {c['title']}",
            "",
            f"**Component ID:** `{c['id']}`",
            "",
            "## Code / infra under analysis (Phases 1–9)",
        ]
        lines.extend(f"- `{p}`" for p in c["code"])
        lines += [
            "",
            "## Data-flow diagram",
            "",
            "```mermaid",
            c["dfd"],
            "```",
            "",
            "## STRIDE analysis",
            "",
            "| Threat | AI/platform-specific risk | Mitigation in this build |",
            "|--------|---------------------------|--------------------------|",
        ]
        for key, name in LETTERS:
            lines.append(
                f"| {name} | {c['threats'][key]} | {c['mitigations'][key]} |"
            )
        lines += [
            "",
            "## Residual risk summary",
            "",
            c["residual"],
            "",
            "> Assurance boundary (G-001): portfolio Design/Local evidence — not ATO.",
            "",
        ]
        (ROOT / f"{c['id']}.md").write_text("\n".join(lines), encoding="utf-8")

    idx = [
        "# security/stride/",
        "",
        "Per-component STRIDE worksheets (10) with data-flow diagrams bound to code from Phases 1–9.",
        "",
        "| # | Worksheet |",
        "|---|-----------|",
    ]
    for i, c in enumerate(COMPONENTS, 1):
        idx.append(f"| {i} | [{c['title']}]({c['id']}.md) |")
    idx.append("")
    (ROOT / "README.md").write_text("\n".join(idx), encoding="utf-8")
    print(f"wrote {len(COMPONENTS)} worksheets")


if __name__ == "__main__":
    main()
