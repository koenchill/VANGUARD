{{ config(
    materialized='incremental',
    unique_key='dataset_version',
    incremental_strategy='merge'
) }}

-- Curation transform: keep approved/active records only for lake join enrichment.
select
  dataset_version,
  source_uri,
  curation_stage,
  quality_score,
  pii_scan_result,
  drift_flag,
  hitl_approval_status,
  lineage_parent_id,
  ingested_at,
  approved_at
from {{ ref('stg_dataset_records') }}
where curation_stage in ('approved', 'active')
{% if is_incremental() %}
  and ingested_at > (select coalesce(max(ingested_at), '1970-01-01') from {{ this }})
{% endif %}
