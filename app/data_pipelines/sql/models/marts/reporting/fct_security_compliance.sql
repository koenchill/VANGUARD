{{ config(materialized='table') }}

-- Security/compliance mart surface for Mission BI (Section 5).
-- Populated by CI/security telemetry feeds in later phases; stub schema for dashboards.
select
  cast(current_date as date) as observe_day,
  1.0 as sast_pass_rate,
  1.0 as sca_pass_rate,
  1.0 as dast_pass_rate,
  0 as stride_residual_high,
  0.0 as nist_ai_rmf_coverage_pct,
  1.0 as backup_dr_restore_pass_rate
