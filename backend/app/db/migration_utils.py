"""Helpers for writing portable ADD COLUMN migrations.

Migration scripts here run against SQLite in tests, MySQL in local
development and PostgreSQL in deployment, and the three do not spell types
the same way. Hard-coding SQL that works locally is how a migration passes
every check on a developer machine and then aborts the deploy: build.sh
runs with `set -o errexit`, so one bad ALTER stops the release.

Concretely, the traps these helpers exist to avoid:

  * DATETIME is not a PostgreSQL type at all -- it wants
    TIMESTAMP WITHOUT TIME ZONE.
  * BOOLEAN ... DEFAULT 0 is rejected by PostgreSQL, which will not accept
    a bare integer as a boolean literal.

Rather than maintaining a table of per-dialect spellings, the type is
compiled from the model's own column definition. The migration therefore
cannot disagree with the model it is catching the database up to.
"""

from __future__ import annotations

from sqlalchemy import Table, text
from sqlalchemy.engine import Engine

from app.db.base import Base

# Importing the models package is what REGISTERS every table on
# Base.metadata. Without it the registry is empty and every lookup below
# raises KeyError -- which is exactly what happened the first time these
# helpers ran outside the application, where nothing else had imported the
# models. Kept here rather than in each migration script so a new script
# cannot forget it.
import app.db.models  # noqa: F401


def column_type_sql(table_name: str, column_name: str, engine: Engine) -> str:
    """The connected dialect's own spelling of a mapped column's type.

    Reads the type from the model rather than a hand-written string, so
    the DDL is correct on every supported engine by construction.
    """
    table: Table = Base.metadata.tables[table_name]
    return table.c[column_name].type.compile(dialect=engine.dialect)


def boolean_false_literal(engine: Engine) -> str:
    """How this dialect writes a false boolean default.

    PostgreSQL requires a real boolean literal; MySQL and SQLite store
    booleans as integers and take 0.
    """
    return "false" if engine.dialect.name == "postgresql" else "0"


def column_exists(engine: Engine, table_name: str, column_name: str) -> bool:
    from sqlalchemy import inspect

    return column_name in {
        col["name"] for col in inspect(engine).get_columns(table_name)
    }


def add_column(
    engine: Engine, table_name: str, column_name: str, suffix: str = "NULL"
) -> bool:
    """Adds one column if absent. Returns True when it was added.

    `suffix` carries whatever follows the type -- nullability and any
    default -- since that part is migration-specific.
    """
    if column_exists(engine, table_name, column_name):
        return False

    type_sql = column_type_sql(table_name, column_name, engine)
    with engine.begin() as connection:
        connection.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {type_sql} {suffix}")
        )
    return True
