# DR Failover Runbook

**RTO:** ≤ 4 hours  
**RPO:** ≤ 24 hours  
**Assurance (G-001):** portfolio procedure — not ATO evidence.

## Preconditions
1. Select a **signed** recovery-set manifest from `backup-dr/manifests/`.
2. Verify signature and reject any stale component ID (`tools/recovery_set.py`).
3. Confirm DR vault / secondary region (`dr_secondary_region` tfvars) is healthy.

## Steps
1. Declare incident; use [comms template](comms-template.md).
2. Freeze writes on primary (or rely on PITR/Delta log checkpoint in the manifest).
3. Restore **only** from the chosen manifest components — never mix independent backups.
4. Validate metadata DB ↔ lake lineage consistency before opening traffic.
5. Repoint DNS / Trino / gateway to DR endpoints.
6. Run production-simulation smoke (`tests/production-simulation/`).

## Abort
If any manifest component is stale or signature fails — **stop**. Do not partial-restore.
