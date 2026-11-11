select i.order_id from {{ ref('fact_item') }} i left join {{ ref('fact_order') }} o using(order_id) where o.order_id is null
