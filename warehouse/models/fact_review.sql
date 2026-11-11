select id review_id,order_id,cast(date as date) as day,rating,category from {{ ref('stg_reviews') }}
