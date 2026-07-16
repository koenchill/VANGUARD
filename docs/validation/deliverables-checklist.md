# Section 13 Deliverables Checklist (Definition of Done)

Checked only when a corresponding **Section 14 walkthrough phase** passed with a real
test run — not by code inspection alone. Evidence report:
[`section14-walkthrough-report.md`](section14-walkthrough-report.md).

Assurance boundary (**G-001**): portfolio Local evidence — **not** ATO.

| # | Deliverable | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Full repo tree + top-level READMEs | Checked | Walkthrough P0–P1; tree from Phase 1 |
| 2 | Docker resource contracts consumed by K8s/Karpenter | Checked | P1 `test_render_resources`; P2 `test_k8s_manifests` |
| 3 | Curation metadata DB schema (stages, quality/PII/drift, HITL) | Checked | P5 promotion + models used in integration tests |
| 4 | Lineage/versioning resolves exact dataset versions | Checked | P5 promotion + G-010 contract `dataset_version` binding |
| 5 | dbt marts + EXPLAIN full-scan CI gate | Checked | P5 `test_explain_full_scan` |
| 6 | Trino-only query path (G-005); no multi-engine abstraction | Checked | P2/P6 BI datasources; module `trino-query-engine` |
| 7 | Enterprise transfer module + landing | Checked | P4 ingestion; `modules/data-transfer` wired |
| 8 | Bulk landing → validate → quarantine | Checked | P4 `test_enterprise_ingestion` |
| 9 | Ongoing sync distinct from bulk | Checked | P4 separate-module + path tests |
| 10 | Cutover plan documented | Deferred | Org/ops runbook — owner: Forward-Deployed Eng (open) |
| 11 | Dual-path BI (PowerBI Windows gateway + Grafana oauthPassThru) | Checked (Local) | P6 BI dual-path; Cloud failover still open (G-003) |
| 12 | OPA RLS primary + four minimum dashboards | Checked (Local) | P3 OPA eval; P6 dashboards + RLS counts |
| 13 | HNSW params explicit on Milvus adapter | Checked | P9 agent stack RAG tests |
| 14 | `infra/terraform/app/` tfvars-only; CI fails on `.tf` | Checked | P0/P2 terraform separation |
| 15 | Daily/weekly backup + signed recovery-set manifests | Checked (Local) | P7 G-006 stale rejection |
| 16 | DR runbook RTO≤4h / RPO≤24h | Checked (Design+Local) | `backup-dr/dr-runbooks/`; live drill Cloud-open |
| 17 | Full test pyramid (unit/integration/load/chaos/security/agent-eval/prod-sim) | Checked | P8–P11 suites; 100 pytest Local pass |
| 18 | STRIDE worksheets for all 10 components | Checked | P3 `test_ten_stride_worksheets…` |
| 19 | ATT&CK + ATLAS playbooks (LLM poisoning + ≥2 more) | Checked | P3 playbook resource refs |
| 20 | AI gateway policy-as-code + tool scopes | Checked | P9 gateway + G-013 suites |
| 21 | OPA/Kyverno forbid privileged/root + sandbox RuntimeClass | Checked (Local) | P3 Kyverno/RuntimeClass; live admission Cloud-open (G-017) |
| 22 | G-013 approval protocol attack suite | Checked | P9 G-013 tests |
| 23 | G-018 audit schema + tamper/deletion/replay drills | Checked (Local) | P9 G-018 drills; live WORM pipeline Cloud-open |
| 24 | CI SHA-pinned Actions + disposable DAST pattern | Checked (Local) | P8 CI gate tests; live Actions run Cloud-open |

**Deferred / open risks (explicit):**

| Item | Owner | Reason |
|------|-------|--------|
| Cutover plan execution (#10) | Forward-Deployed Eng | Requires live legacy source |
| PowerBI tenant failover (G-003 Cloud) | Platform + Identity | Vendor tenant proof |
| Live Trino 4-identity audit (G-004 Cloud) | Platform + Identity | Real Kerberos/OAuth env |
| 10TB-scale benchmark (G-011 Cloud) | Perf Eng | Representative volume in tenant |
| gVisor escape on target EKS (G-017 Cloud) | Platform SRE | Cluster admission proof |
| Live WORM Object Lock pipeline (G-018 Cloud) | SecEng | AWS compliance-mode bucket |
| Org AO sign-offs (G-001/G-012 org) | AO / Security Architect | Not closeable by code |
| Air-gap mirror / FinOps quota (G-020/G-021) | Supply-chain / FinOps | Program investment |
