# Table: accounts

Purpose: Trading accounts, one per desk.
Rows: 6

## Columns
- account_id (integer) — primary key
- name (text) — account name
- desk (text) — Systematic, Market Making, Macro, Stat Arb, Execution, Prop
- base_currency (text)
- opened_on (date)

## Query guidance
- Join via orders.account_id or positions_eod.account_id.
- Desk-level questions ("which desk traded most") group on accounts.desk.