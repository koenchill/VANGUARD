# backup-dr/

Daily/weekly backup policy defs, signed recovery-set manifests (G-006), and DR
runbooks with RTO ≤ 4h / RPO ≤ 24h. Manifest generation: `tools/generate_recovery_manifest.py`
/ `tools/recovery_set.py`. Restores always use a verified manifest — never mixed
independent component backups.
