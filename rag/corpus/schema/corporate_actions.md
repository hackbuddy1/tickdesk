# Table: corporate_actions

Purpose: Splits, dividends and mergers with their ex-dates.
Rows: ~16

## Columns
- action_id (integer) — primary key
- symbol (text)
- ex_date (date) — ex-date of the action
- action_type (text) — 'DIVIDEND', 'SPLIT', 'MERGER'
- ratio (double precision) — populated for SPLIT only
- cash_amount (double precision) — populated for DIVIDEND only
- note (text)

## Query guidance
- ratio and cash_amount are mutually exclusive; filter on action_type first.
- MERGER rows have both ratio and cash_amount NULL.

## Relationships
- corporate_actions.symbol -> instruments.symbol