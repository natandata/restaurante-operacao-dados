select d.day,d.weekday,d.temperature,d.rain,d.promotion,
 count(o.order_id) orders,count(o.order_id) filter(where o.status='concluido') completed,
 count(o.order_id) filter(where o.status='cancelado') cancelled,
 coalesce(sum(o.net_cents),0) net_cents,coalesce(sum(o.contribution_cents),0) contribution_cents,
 avg(o.prep_minutes) filter(where o.status='concluido') prep_minutes
 from {{ ref('dim_date') }} d left join {{ ref('fact_order') }} o using(day) group by all
