from __future__ import annotations
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

MAX_LIMIT = 1000

FORBIDDEN_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
    exp.Alter, exp.TruncateTable, exp.Command, exp.Merge,
)

DANGEROUS_FUNCS = {
    "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_stat_file",
    "pg_sleep", "lo_import", "lo_export", "dblink", "dblink_connect",
    "dblink_exec", "set_config", "pg_terminate_backend", "pg_cancel_backend",
    "pg_reload_conf", "query_to_xml", "pg_read_server_files",
}

_SYSTEM_SCHEMAS = {"pg_catalog", "information_schema", "pg_toast"}


class SQLGuardError(Exception):
    """reject hone pe raise. message dikhana safe hai."""


def validate_and_rewrite(sql: str, allowed_tables: set[str], max_limit: int = MAX_LIMIT) -> str:
   
    try:
        statements = [s for s in sqlglot.parse(sql, dialect="postgres") if s is not None]
    except ParseError as e:
        raise SQLGuardError(f"could not parse SQL: {str(e).splitlines()[0]}")

   
    if len(statements) != 1:
        raise SQLGuardError("only a single statement is allowed")
    stmt = statements[0]

    for node_type in FORBIDDEN_NODES:
        if stmt.find(node_type) is not None:
            raise SQLGuardError(f"'{node_type.__name__.upper()}' is not allowed")

    if not isinstance(stmt, (exp.Select, exp.Union)):
        raise SQLGuardError("only SELECT queries are allowed")

    cte_names = {cte.alias for cte in stmt.find_all(exp.CTE)}
    for table in stmt.find_all(exp.Table):
        if table.name in cte_names:
            continue
        if table.db and table.db.lower() in _SYSTEM_SCHEMAS:
            raise SQLGuardError("system catalog access is not allowed")
        if table.name not in allowed_tables:
            raise SQLGuardError(f"table '{table.name}' is not accessible")

    for fn in stmt.find_all(exp.Anonymous):
        if (fn.name or "").lower() in DANGEROUS_FUNCS:
            raise SQLGuardError(f"function '{fn.name}' is not allowed")

    stmt = _enforce_limit(stmt, max_limit)
    return stmt.sql(dialect="postgres")


def _enforce_limit(stmt: exp.Expression, max_limit: int) -> exp.Expression:
    limit = stmt.args.get("limit")
    if limit is None:
        return stmt.limit(max_limit)
    try:
        current = int(limit.expression.name)
    except (AttributeError, ValueError):
        raise SQLGuardError("LIMIT must be an integer literal")
    return stmt.limit(max_limit) if current > max_limit else stmt
