select * from {{ ref('mart_inventory') }} where closing<0
