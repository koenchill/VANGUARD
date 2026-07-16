# security/k8s-container-hardening/

OPA/Kyverno policies forbidding privileged pods and root execution, plus gVisor/Kata
sandbox RuntimeClass configs (G-017). Trino RLS Rego enforces G-004 identity
propagation (fail closed).

| Artifact | Role |
|----------|------|
| `opa-trino-rls.rego` | Row filters on mission_id + classification |
| `kyverno-deny-privileged-root.yaml` | Enforce deny privileged + require UID 8888 |
| `runtimeclass-sandbox.yaml` | gVisor/Kata on `sandbox-runtime` NodePool |
| `fixtures/deliberately-privileged-pod.yaml` | Negative admission fixture |
