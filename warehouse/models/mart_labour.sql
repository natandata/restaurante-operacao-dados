with s as (select day,sum(hours) as hours,sum(cost_cents) labour_cost_cents from {{ ref('fact_shift') }} group by day)
 select d.day,d.completed,s.hours,s.labour_cost_cents,d.completed/nullif(s.hours,0) orders_per_hour,
 d.contribution_cents-s.labour_cost_cents contribution_after_labour_cents
 from {{ ref('mart_daily') }} d join s using(day)
