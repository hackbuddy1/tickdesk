CREATE INDEX IF NOT EXISTS ticks_symbol_ts_idx ON ticks (symbol, ts DESC);

CREATE MATERIALIZED VIEW bars_1s
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 second', ts) AS bucket,
    symbol,
    first(price, ts) AS open,
    max(price) AS high,
    min(price) AS low,
    last(price, ts) AS close,
    sum(qty) AS volume,
    sum(price * qty) / NULLIF(sum(qty), 0) AS vwap,
    count(*) AS n_ticks
FROM ticks
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('bars_1s',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 second',
    schedule_interval => INTERVAL '30 seconds');

CALL refresh_continuous_aggregate('bars_1s', NULL, NULL);

ANALYZE ticks;
