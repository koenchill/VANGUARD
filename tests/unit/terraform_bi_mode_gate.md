# Air-gapped BI mode fixture for Section 14 Phase 2 gate
# Copy keys into a throwaway tfvars and confirm:
#   module.powerbi_gateway_cluster.enabled == false when bi_deployment_mode == "air_gapped"
#
# Do NOT place this file under infra/terraform/app/ (tfvars JSON only: dev + prod).

bi_deployment_mode_for_test = "air_gapped"
expected_powerbi_gateway_enabled = false
