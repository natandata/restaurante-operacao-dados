select i.order_id,i.product_id,o.day,o.channel,o.status,i.quantity,i.gross_cents,i.food_cost_cents
 from {{ ref('stg_order_items') }} i join {{ ref('fact_order') }} o on o.order_id=i.order_id
