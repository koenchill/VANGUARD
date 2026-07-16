# infra/ansible/

Configuration management for non-Kubernetes workloads. Today this hosts the
PowerBI Windows gateway cluster playbooks (G-003) — justified as an addition
beyond the Section 1 tree because Phase 8 requires `infra/ansible/powerbi-gateway/`
and Terraform user-data explicitly defers gateway install here.
