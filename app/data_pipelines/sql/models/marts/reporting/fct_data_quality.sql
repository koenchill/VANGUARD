{{ config(materialized='table') }}

select
  date_trunc('day', ingested_at) as ingest_day,
  source_uri,
  avg(quality_score) as avg_quality_score,
  sum(case when drift_flag then 1 else 0 end) * 1.0 / nullif(count(*), 0) as drift_rate
from {{ ref('curated_datasets') }}
group by 1, 2
