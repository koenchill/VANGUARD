# security/grc/

Policy docs mapped to NIST AI RMF, audit schema (G-018), WORM destination wiring,
hash-chained audit pipeline, and separated IAM roles (operator vs evidence reader).

| Artifact | Role |
|----------|------|
| `audit-schema.json` | Event schema |
| `audit_pipeline.py` | Hash-chained append-only store |
| `worm-destination.yaml` | Object Lock + OpenSearch |
| `iam-*.json` | Separation of duty |
| `nist-ai-rmf-mapping.md` | Function → control map |
