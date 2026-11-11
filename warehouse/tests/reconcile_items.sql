select o.order_id from {{ ref('fact_order') }} o left join {{ ref('fact_item') }} i using(order_id) group by o.order_id,o.gross_cents having coalesce(sum(i.gross_cents),0)<>o.gross_cents
