# security/mitre-attack/

ATT&CK for Enterprise and MITRE ATLAS mappings covering conventional infra and AI/agent
attack techniques. Playbook procedures live in `security/playbooks/ai-incident-response/`.

| Framework | Technique | Title | Primary detection | Owner |
|-----------|-----------|-------|-------------------|-------|
| ATLAS | AML.M0015 | LLM Prompt Injection / Jailbreak | AI Gateway token/eval anomaly (`app/gateway`) | AI Security On-Call |
| ATLAS | AML.T0043 | Exploiting Analytical Trust | BI provenance / quality_score reconcile | Mission BI + Data Eng |
| ATLAS | AML.T0010 | ML Supply Chain Compromise | SBOM/cosign + pinned Actions | Platform DevSecOps |
| ATLAS | AML.T0024 | Exfiltration via ML Inference API | Gateway egress allow-list (G-012) | AI Security On-Call |
| ATLAS | AML.T0044 | RAG Poisoning | curated-only ingest (`app/rag/ingestion.py`) | Data Eng |
| ATLAS | AML.T0051 | LLM Plugin / Tool Compromise | G-013 + tool scope manifests | Agentic Platform |
| ATT&CK | T1195 | Supply Chain Compromise | Semgrep/Trivy/SBOM gates | Platform DevSecOps |
| ATT&CK | T1611 | Escape to Host | Kyverno deny privileged/root + gVisor/Kata | Platform SRE |
| ATT&CK | T1530 | Data from Cloud Storage Object | Transfer IAM read-only + landing quarantine | Data Eng |
| ATT&CK | T1078 | Valid Accounts | OIDC fail-closed; Kerberos/OAuth passthrough (G-004) | Identity |
