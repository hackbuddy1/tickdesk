"""Adversarial tests for the SQL guard.
Run: pytest -q backend/tests/test_guards.py"""
from app.agent.guards import validate_and_rewrite, SQLGuardError 
import pytest

TABLES = {"ticks", "bars_1s"}

REJECT = [
    ("DROP TABLE ticks",                                     "DROP"),
    ("SELECT * FROM ticks; DROP TABLE ticks",                "single statement"),
    ("DELETE FROM ticks WHERE 1=1",                          "DELETE"),
    ("UPDATE ticks SET price=0",                             "UPDATE"),
    ("INSERT INTO ticks VALUES (1)",                         "INSERT"),
    ("TRUNCATE ticks",                                       "not allowed"),
    ("ALTER TABLE ticks ADD COLUMN x int",                   "ALTER"),
    ("WITH d AS (DELETE FROM ticks RETURNING *) SELECT * FROM d", "DELETE"),
    ("SELECT * FROM users",                                  "not accessible"),
    ("SELECT * FROM pg_catalog.pg_tables",                   "system catalog"),
    ("SELECT symbol FROM ticks UNION SELECT usename FROM pg_user", "not accessible"),
    ("SELECT * FROM ticks WHERE symbol IN (SELECT s FROM secrets)", "not accessible"),
    ("SELECT pg_sleep(10)",                                  "not allowed"),
    ("SELECT pg_read_file('/etc/passwd')",                   "not allowed"),
    ("SELECT * FROM ticks WHERE (SELECT lo_import('/etc/passwd'))", "not allowed"),
    ("this is not sql at all !!!",                           "parse"),
]

ACCEPT = [
    ("SELECT symbol, price FROM ticks WHERE symbol='AAPL'",  "LIMIT 1000"),
    ("SELECT * FROM ticks LIMIT 5000000",                    "LIMIT 1000"),
    ("SELECT * FROM ticks LIMIT 50",                         "LIMIT 50"),
    ("SELECT symbol, avg(close) FROM bars_1s GROUP BY symbol", "LIMIT 1000"),
    ("WITH r AS (SELECT * FROM ticks) SELECT symbol FROM r", "LIMIT 1000"),
]


@pytest.mark.parametrize("sql,reason", REJECT)
def test_rejected(sql, reason):
    with pytest.raises(SQLGuardError) as e:
        validate_and_rewrite(sql, TABLES)
    assert reason.lower() in str(e.value).lower()


@pytest.mark.parametrize("sql,frag", ACCEPT)
def test_accepted(sql, frag):
    out = validate_and_rewrite(sql, TABLES)
    assert frag in out
