# DR Communications Template

**Subject:** [VANGUARD] DR failover in progress — {checkpoint_id}

**Body:**
- Incident commander: {name}
- Manifest: `backup-dr/manifests/{checkpoint_id}.json`
- RTO clock start: {utc_timestamp}
- RPO bound: manifest captured_at {captured_at}
- Status page / bridge: {link}
- Next update: +30 minutes

**Do not** authorize component-level restores outside the signed manifest.
