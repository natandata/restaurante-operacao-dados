select i.ingredient_id,i.name,i.unit,i.reorder_level,i.opening+coalesce(sum(m.quantity),0) closing,
 -coalesce(sum(m.quantity) filter(where m.kind='perda'),0) waste,
 -coalesce(sum(m.quantity) filter(where m.kind='consumo'),0) consumed
 from {{ ref('dim_ingredient') }} i left join {{ ref('fact_movement') }} m using(ingredient_id) group by i.ingredient_id,i.name,i.unit,i.reorder_level,i.opening
