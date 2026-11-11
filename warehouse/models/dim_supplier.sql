select id supplier_id,name from {{ ref('stg_suppliers') }}
