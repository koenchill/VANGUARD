# infra/docker/requirements/

Per-workload dependency manifests. Images install from the committed `*.lock` files into `/opt/venv` (never `pip install --user`). Loose `*.txt` files document the direct dependencies; locks are authoritative for builds (G-008).
