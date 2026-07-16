# ADR: Model / Mission-Data Boundary (G-012)

- **Status:** Accepted (Design-level portfolio decision)
- **Date:** 2026-07-16
- **Deciders:** Platform Architecture, AI Security, Data Governance
- **Assurance:** Design evidence only — provider contract terms and AO sign-off remain open (Section 15)

## Context

Mission data must not train provider models, must not egress to unapproved destinations,
and must not be retained beyond an operator-configured short-lived audit window.
Inference must not use the public internet from the inference path.

## Decision

1. **Private connectivity only:** Model inference uses a VPC-internal endpoint. The
   `inference-gpu` NodePool has no public internet egress for the inference path.
2. **No training / minimal retention:** Provider deployment contractually commits to no
   training on submitted data and no prompt/response retention beyond the audit logging
   window used for G-018.
3. **Approved data classes:** `U`, `FOUO` (default portfolio). Higher classifications
   require an explicit ADR amendment before gateway allow.
4. **Approved egress destinations:** Only the private model endpoint hostname(s) listed
   in environment tfvars / gateway config (`approved_model_egress`).
5. **Encryption:** TLS in transit; CMEK/KMS at rest for stored prompts in the audit window.
6. **Regional residency:** `us-gov-west-1` primary; DR secondary per `dr_secondary_region`.
7. **Fallback model:** On primary-provider outage, fail closed to a pre-approved secondary
   private endpoint — never to a public SaaS URL.
8. **Enforcement point:** `app/gateway/gateway.py` `enforce_model_boundary()` denies
   over-classification and non-approved egress **before** any model call.

## Consequences

- Negative tests must prove deny for over-class and bad egress (Local: unit tests; Cloud-Integration: live gateway).
- Provider AO paperwork is out of band for this portfolio repo (G-001).

## References

- Section 12 G-012 baseline
- `security/playbooks/ai-incident-response/aml-t0024-model-exfiltration.md`
- `app/gateway/gateway.py`
