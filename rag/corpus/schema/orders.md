# Table: orders

Purpose: Submitted orders with side, type, quantity and lifecycle status.
Rows: ~5,000

## Columns
- order_id (bigint) — primary key
- ts (timestamptz) — submission time
- account_id (integer) — submitting account
- symbol (text)
- side (text) — 'BUY' or 'SELL'
- order_type (text) — 'MARKET' or 'LIMIT'
- limit_price (double precision) — NULL for MARKET orders
- qty (integer) — requested quantity
- status (text) — 'FILLED', 'PARTIAL', 'CANCELLED', 'REJECTED'

## Query guidance
- An order is only executed if status is FILLED or PARTIAL; CANCELLED and
  REJECTED orders have no rows in `fills`.
- Requested quantity lives here (orders.qty); executed quantity lives in fills.qty.
  Do not use orders.qty as executed volume.
- limit_price IS NULL is equivalent to order_type = 'MARKET'.

## Relationships
- orders.account_id -> accounts.account_id
- orders.symbol -> instruments.symbol
- fills.order_id -> orders.order_id