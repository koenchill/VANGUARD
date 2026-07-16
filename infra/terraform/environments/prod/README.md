# environments/prod

Production environment root: wires every module from Section 7 (+ observability) with values from `../../app/prod.tfvars.json`. Isolated S3 backend + DynamoDB lock (partial backend config). Requires Terraform `>= 1.15.0`.
