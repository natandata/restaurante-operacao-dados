select id receipt_id,cast(date as date) as day,ingredient_id,quantity,supplier_id from {{ ref('stg_receipts') }}
