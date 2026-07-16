# infra/ansible/powerbi-gateway/

Installs Microsoft’s **standard on-premises data gateway** on the two Windows
Server EC2 members from `modules/powerbi-gateway-windows`, joins them into one
gateway cluster (vendor HA), and configures **Kerberos constrained delegation**
so Trino sees the real PowerBI viewer identity (G-003 / G-004).

This is not a Kubernetes workload and must never be containerized.
