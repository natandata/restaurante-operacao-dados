select day,channel,count(*) orders,avg(prep_minutes) prep_minutes,
 count(*) filter(where prep_minutes>promised_minutes) late_orders from {{ ref('fact_order') }} where status='concluido' group by all
