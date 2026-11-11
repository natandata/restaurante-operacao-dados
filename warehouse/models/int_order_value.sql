select *,gross_cents-discount_cents-fee_cents as calculated_net_cents from {{ ref('stg_orders') }}
