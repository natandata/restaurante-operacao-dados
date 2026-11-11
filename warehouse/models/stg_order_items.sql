{{ config(materialized='view') }}
select * from {{ source('raw','order_items') }}
