"""Migration: add users.is_system_admin.

Why this is a script and not just init_db.py
--------------------------------------------
Base.metadata.create_all creates MISSING TABLES but never adds MISSING
COLUMNS to a table that already exists. users already exists on every
deployment, so this column has to be added explicitly or every query
selecting it fails -- including login, since SQLAlchemy names each mapped
column in its SELECT.

Idempotent and dialect-agnostic (SQLite, MySQL, PostgreSQL): the live
schema is inspected first, so re-running against an already-migrated
database is a no-op. Safe to leave wired into build.sh permanently.

Existing rows default to false. That is deliberate -- the migration grants
nobody protection. The system admin is designated only by
app/cli/create_system_admin.py, so this script can never silently elevate
an account.

Usage:
    python migrate_add_system_admin.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.db.session import engine

TABLE = "users"
COLUMN = "is_system_admin"


def column_exists() -> bool:
    return COLUMN in {col["name"] for col in inspect(engine).get_columns(TABLE)}


def main() -> int:
    if TABLE not in inspect(engine).get_table_names():
        # A brand-new database has no users table yet; init_db.py will
        # create it from the model, column included. Nothing to migrate.
        print(f"Table '{TABLE}' does not exist yet -- nothing to migrate.")
        return 0

    if column_exists():
        print(f"{TABLE}.{COLUMN} already present -- nothing to do.")
        return 0

    # BOOLEAN with a 0 default is accepted by SQLite, MySQL and PostgreSQL
    # alike; NOT NULL plus the default backfills every existing row in one
    # statement without a separate UPDATE pass.
    statement = text(
        f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} BOOLEAN NOT NULL DEFAULT 0"
    )

    with engine.begin() as connection:
        connection.execute(statement)

    if not column_exists():
        print(f"FAILED: {TABLE}.{COLUMN} still absent after the migration.")
        return 1

    print(f"Added {TABLE}.{COLUMN} (existing rows default to false).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
