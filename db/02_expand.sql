BEGIN;

CREATE TABLE IF NOT EXISTS instruments (
    symbol text PRIMARY KEY,
    name text NOT NULL,
    sector text NOT NULL,
    exchange text NOT NULL,
    currency text NOT NULL DEFAULT 'USD',
    lot_size integer NOT NULL DEFAULT 1,
    tick_size double precision NOT NULL DEFAULT 0.01,
    listed_on date
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id integer PRIMARY KEY,
    name text NOT NULL,
    desk text NOT NULL,
    base_currency text NOT NULL DEFAULT 'USD',
    opened_on date NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id bigserial PRIMARY KEY,
    ts timestamptz NOT NULL,
    account_id integer NOT NULL REFERENCES accounts(account_id),
    symbol text NOT NULL REFERENCES instruments(symbol),
    side text NOT NULL CHECK (side IN ('BUY','SELL')),
    order_type text NOT NULL CHECK (order_type IN ('MARKET','LIMIT')),
    limit_price double precision,
    qty integer NOT NULL CHECK (qty > 0),
    status text NOT NULL CHECK (status IN ('FILLED','PARTIAL','CANCELLED','REJECTED'))
);
CREATE INDEX IF NOT EXISTS orders_ts_idx ON orders (ts DESC);
CREATE INDEX IF NOT EXISTS orders_symbol_ts_idx ON orders (symbol, ts DESC);
CREATE INDEX IF NOT EXISTS orders_acct_ts_idx ON orders (account_id, ts DESC);

CREATE TABLE IF NOT EXISTS fills (
    fill_id bigserial PRIMARY KEY,
    order_id bigint NOT NULL REFERENCES orders(order_id),
    ts timestamptz NOT NULL,
    symbol text NOT NULL REFERENCES instruments(symbol),
    price double precision NOT NULL,
    qty integer NOT NULL CHECK (qty > 0),
    fee double precision NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS fills_order_idx ON fills (order_id);
CREATE INDEX IF NOT EXISTS fills_symbol_ts_idx ON fills (symbol, ts DESC);

CREATE TABLE IF NOT EXISTS positions_eod (
    as_of date NOT NULL,
    account_id integer NOT NULL REFERENCES accounts(account_id),
    symbol text NOT NULL REFERENCES instruments(symbol),
    net_qty integer NOT NULL,
    avg_cost double precision NOT NULL,
    PRIMARY KEY (as_of, account_id, symbol)
);

CREATE TABLE IF NOT EXISTS corporate_actions (
    action_id serial PRIMARY KEY,
    symbol text NOT NULL REFERENCES instruments(symbol),
    ex_date date NOT NULL,
    action_type text NOT NULL CHECK (action_type IN ('DIVIDEND','SPLIT','MERGER')),
    ratio double precision,
    cash_amount double precision,
    note text
);
CREATE INDEX IF NOT EXISTS corp_actions_symbol_idx ON corporate_actions (symbol, ex_date DESC);

COMMIT;