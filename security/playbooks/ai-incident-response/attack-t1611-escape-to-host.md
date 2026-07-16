# Playbook — K8s Escape to Host (ATT&CK T1611)

**Mapped resources:** `security/k8s-container-hardening/kyverno-deny-privileged.yaml`,
`runtimeclass-gvisor.yaml`, `sandbox-runtime` NodePool.

## Detection
Admission controller deny of privileged/root pod; unexpected RuntimeClass.

## Containment
Keep default-deny NetworkPolicies; cordon node if escape suspected; snapshot forensics.

## Triage & Rollback
Rebuild node from immutable AMI; review Kyverno policy exceptions (none expected).

**Owner:** Platform SRE
