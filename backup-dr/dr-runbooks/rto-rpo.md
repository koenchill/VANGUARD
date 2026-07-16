# RTO / RPO Targets

| Objective | Target | Measurement |
|-----------|--------|-------------|
| RTO | ≤ 4 hours | Incident declare → production-simulation smoke green on DR |
| RPO | ≤ 24 hours | Manifest `captured_at` vs last committed mission write |

Daily and weekly policies both emit signed recovery-set manifests so restores remain
coherent (G-006). Cross-region copy is configured in `modules/backup-dr`.
