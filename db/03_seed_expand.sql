BEGIN;
INSERT INTO instruments (symbol, name, sector, exchange, currency, lot_size, tick_size, listed_on)
SELECT
    s.symbol,
    s.symbol || ' Corporation',
    (ARRAY['Technology','Financials','Energy','Healthcare','Consumer'])
        [1 + (abs(hashtext(s.symbol)) % 5)],
    (ARRAY['NASDAQ','NYSE'])[1 + (abs(hashtext(s.symbol)) % 2)],
    'USD',
    (ARRAY[1,10,100])[1 + (abs(hashtext(s.symbol)) % 3)],
    0.01,
    DATE '2005-01-01' + (abs(hashtext(s.symbol)) % 6000)
FROM (SELECT DISTINCT symbol FROM ticks) s
ON CONFLICT (symbol) DO NOTHING;

-- accounts: 6 fixed desks
INSERT INTO accounts (account_id, name, desk, base_currency, opened_on) VALUES
    (1, 'Alpha Systematic', 'Systematic', 'USD', DATE '2019-03-14'),
    (2, 'Beta Market Making','Market Making','USD', DATE '2020-07-01'),
    (3, 'Gamma Macro','Macro','USD', DATE '2018-11-22'),
    (4, 'Delta Stat Arb','Stat Arb','USD', DATE '2021-05-09'),
    (5, 'Epsilon Execution', 'Execution','USD', DATE '2022-01-17'),
    (6, 'Zeta Prop','Prop','USD', DATE '2023-08-30')
ON CONFLICT (account_id) DO NOTHING;

WITH sample AS (
    SELECT ts, symbol, price, random() AS r1, random() AS r2, random() AS r3
    FROM ticks
    ORDER BY random()
    LIMIT 5000
)
INSERT INTO orders (ts, account_id, symbol, side, order_type, limit_price, qty, status)
SELECT
    ts,
    1 + (abs(hashtext(symbol || ts::text)) % 6),
    symbol,
    CASE WHEN r1 < 0.5 THEN 'BUY' ELSE 'SELL' END,
    CASE WHEN r2 < 0.7 THEN 'LIMIT' ELSE 'MARKET' END,
    CASE WHEN r2 < 0.7 THEN round((price * (0.98 + r3 * 0.04))::numeric, 2)::double precision END,
    (1 + (abs(hashtext(ts::text)) % 20)) * 100,
    CASE
        WHEN r3 < 0.70 THEN 'FILLED'
        WHEN r3 < 0.85 THEN 'PARTIAL'
        WHEN r3 < 0.95 THEN 'CANCELLED'
        ELSE 'REJECTED'
    END
FROM sample;

INSERT INTO fills (order_id, ts, symbol, price, qty, fee)
SELECT
    o.order_id,
    o.ts + (random() * interval '900 milliseconds'),
    o.symbol,
    COALESCE(o.limit_price, t.price) * (0.999 + random() * 0.002),
    CASE WHEN o.status = 'FILLED' THEN o.qty
         ELSE GREATEST(100, (o.qty * (0.2 + random() * 0.6))::int) END,
    round((o.qty * 0.0015)::numeric, 4)::double precision
FROM orders o
LEFT JOIN LATERAL (
    SELECT price FROM ticks
    WHERE ticks.symbol = o.symbol AND ticks.ts <= o.ts
    ORDER BY ticks.ts DESC LIMIT 1
) t ON true
WHERE o.status IN ('FILLED','PARTIAL')
  AND NOT EXISTS (SELECT 1 FROM fills f WHERE f.order_id = o.order_id);

INSERT INTO positions_eod (as_of, account_id, symbol, net_qty, avg_cost)
SELECT
    f.ts::date,
    o.account_id,
    f.symbol,
    SUM(CASE WHEN o.side = 'BUY' THEN f.qty ELSE -f.qty END)::int,
    (SUM(f.price * f.qty) / NULLIF(SUM(f.qty), 0))
FROM fills f
JOIN orders o ON o.order_id = f.order_id
GROUP BY f.ts::date, o.account_id, f.symbol
ON CONFLICT (as_of, account_id, symbol) DO NOTHING;

INSERT INTO corporate_actions (symbol, ex_date, action_type, ratio, cash_amount, note)
SELECT
    symbol,
    DATE '2024-01-01' + (abs(hashtext(symbol)) % 700),
    CASE WHEN abs(hashtext(symbol)) % 3 = 0 THEN 'SPLIT'
         WHEN abs(hashtext(symbol)) % 3 = 1 THEN 'DIVIDEND'
         ELSE 'MERGER' END,
    CASE WHEN abs(hashtext(symbol)) % 3 = 0 THEN 2.0 END,
    CASE WHEN abs(hashtext(symbol)) % 3 = 1
         THEN round((0.2 + (abs(hashtext(symbol)) % 300) / 100.0)::numeric, 2)::double precision END,
    'auto-generated reference data'
FROM instruments
WHERE abs(hashtext(symbol)) % 2 = 0;

COMMIT;