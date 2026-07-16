{{ config(materialized='view') }}

-- Staging projection of curation metadata for dbt tests / marts.
select
  id,
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
from {{ source('curation_metadata', 'dataset_records') }}
