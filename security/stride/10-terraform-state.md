# STRIDE Worksheet — Terraform state / backend

**Component ID:** `10-terraform-state`

## Code / infra under analysis (Phases 1–9)
- `infra/terraform/environments/`
- `infra/terraform/backend-configs/`
- `infra/terraform/app/`

## Data-flow diagram

```mermaid
flowchart LR
  DEV[environments/dev] --> S3D[S3 state + DynamoDB lock DEV]
  PROD[environments/prod] --> S3P[S3 state + DynamoDB lock PROD]
  APP[app/dev|prod.tfvars.json] --> DEV
  APP --> PROD
  CI[tflint/checkov] -->|deny .tf under app/| APP
```

## STRIDE analysis

| Threat | AI/platform-specific risk | Mitigation in this build |
|--------|---------------------------|--------------------------|
| Spoofing | Stolen CI role applies to wrong account | Per-env backends; IAM boundary |
| Tampering | State file tampering / drift hide | DynamoDB lock; versioned S3 state |
| Repudiation | Apply without recorded plan | Plan artifacts retained in CI |
| Information Disclosure | Shared state across envs | Isolated state per environment (no shared file) |
| Denial of Service | State lock stuck blocking remediations | Lock timeout runbooks |
| Elevation of Privilege | Hardcoded secrets in modules | Variable-only modules; app/ tfvars JSON only |

## Residual risk summary

Remote backend enablement against GovCloud tenant is Cloud-Integration.

> Assurance boundary (G-001): portfolio Design/Local evidence — not ATO.
