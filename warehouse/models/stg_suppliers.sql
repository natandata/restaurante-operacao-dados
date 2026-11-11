{{ config(materialized='view') }}
select * from {{ source('raw','suppliers') }}
