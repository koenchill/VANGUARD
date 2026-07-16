# infra/terraform/app/

APP CONFIG ONLY — `dev.tfvars.json` and `prod.tfvars.json`. CI fails if any `.tf` file lands here (Section 7 / G-009).

Invoke from an environment root:

```bash
cd infra/terraform/environments/prod
terraform init   # supply backend config for the env
terraform plan -var-file=../../app/prod.tfvars.json
```
