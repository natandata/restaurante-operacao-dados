select channel,count(*) orders,sum(net_cents) net_cents,sum(fee_cents) fee_cents,
 sum(contribution_cents) contribution_cents from {{ ref('fact_order') }} where status='concluido' group by channel
