select cast(date as date) as day,ingredient_id,kind,quantity,source from {{ ref('stg_movements') }}
