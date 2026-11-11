select p.product_id,p.name,p.category,sum(i.quantity) units,sum(i.gross_cents) gross_cents,
 sum(i.gross_cents-i.food_cost_cents) food_margin_cents
 from {{ ref('dim_product') }} p join {{ ref('fact_item') }} i using(product_id)
 where i.status='concluido' group by all
