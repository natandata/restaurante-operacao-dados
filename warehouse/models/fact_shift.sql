select cast(date as date) as day,employee_id,role,hours,cost_cents from {{ ref('stg_shifts') }}
