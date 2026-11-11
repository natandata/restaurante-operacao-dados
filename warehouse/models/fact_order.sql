select id order_id,cast(date as date) as day,cast(created_at as timestamptz) created_at,channel,status,cancel_reason,
 gross_cents,discount_cents,fee_cents,net_cents,food_cost_cents,net_cents-food_cost_cents contribution_cents,
 prep_minutes,promised_minutes from {{ ref('int_order_value') }}
