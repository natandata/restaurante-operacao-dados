select id ingredient_id,name,unit,opening,reorder reorder_level from {{ ref('stg_ingredients') }}
