# Table: instruments

Purpose: Reference data, one row per tradable symbol.
Rows: 20

## Columns
- symbol (text) — primary key, ticker
- name (text) — company name
- sector (text) — Technology, Financials, Energy, Consumer, Automobile, Healthcare, Telecom, Industrials, Materials
- exchange (text) — all instruments currently list on NSE
- currency (text) — INR
- currency (text) — quote currency
- lot_size (integer) — minimum tradable lot
- tick_size (double precision) — minimum price increment
- listed_on (date) — listing date

## Query guidance
- Join here whenever a question groups by sector, exchange, or company name.
- Referenced by ticks, bars_1s, orders, fills, positions_eod, corporate_actions.