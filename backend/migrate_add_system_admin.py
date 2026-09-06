"""Migration: add users.is_system_admin.

Why this is a script and not just init_db.py
--------------------------------------------
Base.metadata.create_all creates MISSING TABLES but never adds MISSING
COLUMNS to a table that already exists. users already exists on every
deployment, so this column has to be added explicitly or every query
selecting it fails -- including login, since SQLAlchemy names each mapped
column in its SELECT.

Idempotent and portable across SQLite, MySQL and PostgreSQL: the live
schema is inspected first, so re-running is a no-op, and the column type
and boolean default are taken from the dialect rather than hard-coded (see
app/db/migration_utils.py -- PostgreSQL rejects `DEFAULT 0` for a boolean).

Existing rows default to false. That is deliberate -- the migration grants
nobody protection. The system admin is designated only by
app/cli/create_system_admin.py, so this script can never silently elevate
an account.

Usage:
    python migrate_add_system_admin.py
"""

from __future__ import annotations

from sqlalchemy import inspect

from app.db.migration_utils import add_column, boolean_false_literal, column_exists
from app.db.session import engine

TABLE = "users"
COLUMN = "is_system_admin"


def main() -> int:
    if TABLE not in inspect(engine).get_table_names():
        # A brand-new database has no users table yet; init_db.py will
        # create it from the model, column included. Nothing to migrate.
        print(f"Table '{TABLE}' does not exist yet -- nothing to migrate.")
        return 0

    if column_exists(engine, TABLE, COLUMN):
        print(f"{TABLE}.{COLUMN} already present -- nothing to do.")
        return 0

    # NOT NULL plus a default backfills every existing row in one statement,
    # with no separate UPDATE pass.
    add_column(
        engine,
        TABLE,
        COLUMN,
        suffix=f"NOT NULL DEFAULT {boolean_false_literal(engine)}",
    )

    # Re-inspect rather than trusting the statement: a silently ignored
    # ALTER would otherwise look like success.
    if not column_exists(engine, TABLE, COLUMN):
        print(f"FAILED: {TABLE}.{COLUMN} still absent after the migration.")
        return 1

    print(f"Added {TABLE}.{COLUMN} (existing rows default to false).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
