# Playbook — Tool-Use Hijacking (ATLAS AML.T0051)

**Mapped resources:** `app/agents/tools.py`, `app/agents/human_in_the_loop.py`,
`app/tools/manifests/`.

## Detection
Tool invocation with resource_scope outside manifest, or HITL digest mismatch
(argument/actor/tool substitution).

## Containment
`ApprovalRejected` fail-closed; revoke signing key if key material suspected;
NetworkPolicy quarantine on repeating agent.

## Triage & Rollback
Replay G-013 audit records; rotate KMS key; redeploy agent with tightened manifests.

**Owner:** Agentic Platform
