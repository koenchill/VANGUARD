# Playbook — LLM Poisoning / Jailbreak (ATLAS AML.M0015)

**Mapped resources (this build):**
- Detection: `app/gateway/policies.yaml`, `app/gateway/gateway.py`
- Containment: `infra/k8s/base/networkpolicies.yaml` (`agent-quarantine`),
  `security/k8s-container-hardening/`
- Rollback: `app/data_pipelines/lineage/`, `app/data_pipelines/promotion/`,
  `backup-dr/` (weekly restore set)
- Forensics: `app/telemetry/events.py` → WORM audit (G-018)

## 1. Detection
AI Gateway flags anomalous outgoing token volume or out-of-bound response-evaluation
scores from the agent eval metrics stream. Signal source is the Kong plugin chain
(rate-limit + pre-function) and gateway logs tagged with `X-End-User-Identity`.

## 2. Containment
Apply the `agent-quarantine` NetworkPolicy label to the suspect pod in namespace
`agentic-app`, diverting traffic to the quarantine path (default-deny remains in force
for non-labeled peers). Do **not** delete pods before memory/tool-call capture.

## 3. Triage & Rollback
1. Resolve the active dataset via `active_dataset_pointer` / lakeFS lineage.
2. Restore to the last verified weekly backup (G-006 recovery-set manifest).
3. Redeploy inference/gateway images with sanitized system prompts (digest-pinned).

## 4. Forensics
Export the agent’s orchestration history and tool-call logs from `telemetry_events`
and the immutable WORM stream. Preserve Gateway decision logs for the incident window.

**Owner:** AI Security On-Call  
**Assurance:** Design + Local wiring; live tabletop vs cluster is Cloud-Integration (§14 P9).
