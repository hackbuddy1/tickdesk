CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE ticks (
    ts     TIMESTAMPTZ      NOT NULL,
    symbol TEXT             NOT NULL,
    price  DOUBLE PRECISION NOT NULL,
    qty    INTEGER          NOT NULL,
    bid    DOUBLE PRECISION NOT NULL,
    ask    DOUBLE PRECISION NOT NULL
);

SELECT create_hypertable('ticks', 'ts', chunk_time_interval => INTERVAL '1 hour');
