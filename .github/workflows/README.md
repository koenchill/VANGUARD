# .github/workflows/

`ci-cd-pipeline.yaml` and `nightly-security.yaml` — SHA-pinned Actions (G-019), SBOM +
cosign, and G-015 DAST against a disposable gateway (`/readyz` → `/openapi.json`).
Production hostnames are hard-blocked (`security/sast-sca-dast/runner-network-policy.yaml`).
