# security/sast-sca-dast/

Scan configurations and published reports for Semgrep SAST, Trivy/Grype SCA, and
authenticated ZAP DAST (G-015).

| Artifact | Role |
|----------|------|
| `semgrep-rules.yaml` | Extra SAST rules (secrets) |
| `finding-policy.yaml` | Fail criteria + planted-path ignores |
| `runner-network-policy.yaml` | Hard-block production DAST hosts |
| `fixtures/planted/` | Deliberate fails for gate dry-run (§14 Phase 8) |
