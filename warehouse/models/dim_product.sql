select id product_id,name,category,price_cents,cost_cents from {{ ref('stg_products') }}
