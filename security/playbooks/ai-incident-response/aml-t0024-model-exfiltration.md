# Playbook — Model / Inference Exfiltration (ATLAS AML.T0024)

**Mapped resources:** `app/gateway/gateway.py` (`enforce_model_boundary`),
`docs/adrs/model-boundary.md` (G-012).

## Detection
Request targets non-approved egress destination or classification above approved
handling level.

## Containment
Gateway denies before model endpoint; alert on repeated deny.

## Triage & Rollback
Review ADR allow-lists; rotate credentials; confirm no public internet egress from
inference NodePool.

**Owner:** AI Security On-Call
