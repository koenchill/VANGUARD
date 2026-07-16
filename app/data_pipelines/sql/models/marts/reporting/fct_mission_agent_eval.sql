{{ config(materialized='table') }}

-- Mission/agent evaluation mart — fed from app/telemetry via dbt (Section 5).
select
  cast(current_date as date) as observe_day,
  0.0 as task_completion_rate,
  0.0 as faithfulness_score,
  0.0 as cost_per_inference,
  0 as mission_scenario_pass_count,
  0 as agent_step_event_count
