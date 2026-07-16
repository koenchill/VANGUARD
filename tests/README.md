# tests/

Production-mimicry test pyramid (Section 9):

| Layer | Path | Gate |
|-------|------|------|
| Unit | `tests/unit/` | renderer, G-013, security artifacts, CI pins |
| Integration | `tests/integration/` | ingestion, promotion, BI dual-path |
| Agent-eval | `tests/agent-eval/` | G-010 deterministic contracts |
| Load | `tests/load/` | G-011 workload-manifest + K6 |
| Chaos | `tests/chaos/` | HITL fail-closed under injection |
| Security | `tests/security/` + CI DAST | G-015 |
| Production simulation | `tests/production-simulation/` | staging release gate |

## Dependencies

```bash
pip install -r tests/requirements.txt
```

`tests/requirements.txt` pins `PyYAML` + `jsonschema` because unit tests import `tools/render_resources.py`.
