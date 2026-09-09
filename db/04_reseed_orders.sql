BEGIN;

DELETE FROM positions_eod;
DELETE FROM fills;
DELETE FROM orders;
ALTER SEQUENCE orders_order_id_seq RESTART WITH 1;
ALTER SEQUENCE fills_fill_id_seq  RESTART WITH 1;

WITH sample AS MATERIALIZED (
    SELECT ts, symbol, price,
           random() AS r1, random() AS r2, random() AS r3
    FROM ticks
    TABLESAMPLE SYSTEM (2)
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

-- fills: sirf FILLED/PARTIAL
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
WHERE o.status IN ('FILLED','PARTIAL');

-- positions_eod
INSERT INTO positions_eod (as_of, account_id, symbol, net_qty, avg_cost)
SELECT
    f.ts::date,
    o.account_id,
    f.symbol,
    SUM(CASE WHEN o.side = 'BUY' THEN f.qty ELSE -f.qty END)::int,
    (SUM(f.price * f.qty) / NULLIF(SUM(f.qty), 0))
FROM fills f
JOIN orders o ON o.order_id = f.order_id
GROUP BY f.ts::date, o.account_id, f.symbol;

COMMIT;