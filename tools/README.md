# tools/

Repo-level build tooling that is neither application code nor Terraform. Houses the resource-contract renderer (`render_resources.py`, invoked as `python tools/render_resources.py`) that turns `infra/docker/resources/*.yaml` into Kubernetes and Karpenter fragments with content digests (G-007).
