# DR Failback Runbook

**RTO credit:** failback does not reset the incident RTO clock until primary is verified.

## Steps
1. Confirm primary region healthy and catch-up replication complete.
2. Generate a fresh daily recovery-set manifest on primary.
3. Quiesce DR writers; restore/sync deltas to primary using the new manifest.
4. Repoint traffic to primary; monitor `/readyz`, Trino, and BI paths.
5. Keep DR warm-standby; schedule post-incident G-018 evidence retrieval.
