{{ config(materialized='table') }}

-- Pre-aggregated reporting mart — the only lake-derived surface BI may query (Section 5).
select
  curation_stage,
  count(*) as record_count,
  avg(quality_score) as avg_quality_score,
  sum(case when drift_flag then 1 else 0 end) as drift_count,
  sum(case when hitl_approval_status = 'approved' then 1 else 0 end) as hitl_approved_count,
  max(ingested_at) as last_ingested_at
from {{ ref('curated_datasets') }}
group by curation_stage
