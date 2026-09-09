# Table: fills

Purpose: Executions against orders. An order may be fully or partially filled.
Rows: ~4,275

## Columns
- fill_id (bigint) — primary key
- order_id (bigint) — the order this execution belongs to
- ts (timestamptz) — execution time
- symbol (text)
- price (double precision) — execution price
- qty (integer) — executed quantity
- fee (double precision) — commission charged

## Query guidance
- Executed notional = SUM(price * qty). Fees are separate, add fee only if asked.
- Average execution price must be volume-weighted:
  SUM(price*qty)/NULLIF(SUM(qty),0). A plain AVG(price) is wrong.
- To get side or account, join back to orders.

## Relationships
- fills.order_id -> orders.order_id
- fills.symbol -> instruments.symbol