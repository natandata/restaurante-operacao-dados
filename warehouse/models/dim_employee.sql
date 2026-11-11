select id employee_id,role,hourly_cents from {{ ref('stg_employees') }}
