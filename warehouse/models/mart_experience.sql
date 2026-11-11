select day,category,count(*) reviews,avg(rating) rating,count(*) filter(where rating<=2) low_ratings
 from {{ ref('fact_review') }} group by all
