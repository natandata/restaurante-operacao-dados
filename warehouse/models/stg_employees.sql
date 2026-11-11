{{ config(materialized='view') }}
select * from {{ source('raw','employees') }}
