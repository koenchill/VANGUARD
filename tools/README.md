# tools/

Repo-level build tooling (not application code):

- `render_resources.py` — Docker resource contracts → K8s/Karpenter fragments + digests (G-007)
- `generate_k8s_manifests.py` — Phase 5 GitOps manifests from those contracts
- `generate_stride_worksheets.py` — Phase 10 STRIDE worksheet generator
- `render_bi_dashboards.py` — dual-path BI dashboard renderer
- `check_explain_full_scan.py` — CI gate for EXPLAIN full-table-scan detection
- `check_terraform_separation.py` — fails if `.tf` lands under `infra/terraform/app/` or modules gain env literals
- `check_cicd_gates.py` — G-015/G-019 Action SHA pins, localhost DAST, planted fixtures
- `link_load_report.py` — bind K6 summaries to G-011 workload-manifest (dataset + code version)
- `recovery_set.py` / `generate_recovery_manifest.py` — G-006 signed recovery-set manifests
- `run_section14_walkthrough.py` — Phase 14 Local walkthrough runner → `docs/validation/`
- `ensure_venv.py` — create repo `.venv` (prefer 3.11) + install `tests/requirements.txt`
- `demo_raw_ingest.py` — Local bulk/ongoing/quarantine raw-ingest demo (JSON summary)
- `stream_local_source.py` — Local CDC/ongoing stream into Grafana marts (integrated-source demo)
- `run_sql_optimization.py` — Local EXPLAIN ANALYZE lab + covering indexes on Mission BI marts
- `prepare_grafana_local.py` — seed Postgres marts + Local Grafana dashboards (no cloud)
- `demo_ingest_to_grafana.py` — Local E2E raw ingest → promote → Grafana Mission BI contract report
- `run_mimic_prod.py` — Local prod-mimicry orchestrator (gateway smoke + pyramid + optional k6) → `docs/validation/mimic-prod-report.*` (see `scripts/`)

