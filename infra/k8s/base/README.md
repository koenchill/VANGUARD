# infra/k8s/base/

Base Deployments/Services (gateway, inference API, curation pipeline), namespaces, and default-deny NetworkPolicies. Container `resources:` blocks are generated from `infra/docker/resources/*.yaml` via `tools/generate_k8s_manifests.py` (G-007) — do not hand-edit CPU/memory/GPU values.
