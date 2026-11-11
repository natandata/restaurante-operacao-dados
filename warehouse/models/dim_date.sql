select cast(date as date) as day,weekday,temperature,rain,promotion from {{ ref('stg_context') }}
