select * from {{ ref('fact_order') }} where status='concluido' and net_cents<>gross_cents-discount_cents-fee_cents
