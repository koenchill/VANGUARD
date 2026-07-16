# tools/

Repo-level build tooling (not application code):

- `render_resources.py` — Docker resource contracts → K8s/Karpenter fragments + digests (G-007)
- `generate_k8s_manifests.py` — Phase 5 GitOps manifests from those contracts
- `check_explain_full_scan.py` — CI gate for EXPLAIN full-table-scan detection
- `check_terraform_separation.py` — fails if `.tf` lands under `infra/terraform/app/` or modules gain env literals

