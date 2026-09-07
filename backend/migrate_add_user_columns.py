"""Migration: bring the users table up to date with the User model.

Why this covers more than one column
------------------------------------
create_all creates MISSING TABLES but never adds MISSING COLUMNS to a table
that already exists, so every column added to User after a database was
first created has to be applied explicitly. Three qualify:

    full_name        added with the Users consolidation feature
    email            added with the Users consolidation feature
    is_system_admin  added with the protected system administrator

Only the last of those ever had a migration. full_name and email were added
to the model with none at all, which means a database created before that
change is still missing them -- and because SQLAlchemy names every mapped
column in its SELECT, an absent column does not break one page, it breaks
every read of the users table. Login included. The symptom is a 500 on
sign-in that looks nothing like a schema problem.

This replaces migrate_add_system_admin.py, which handled only the third.

Idempotent and portable across SQLite, MySQL and PostgreSQL: each column is
checked against the live schema first, so re-running is a no-op and a
partially-applied migration finishes cleanly. Types and the boolean default
are taken from the dialect rather than hard-coded -- see
app/db/migration_utils.py, since PostgreSQL rejects `DEFAULT 0` for a
boolean and has no DATETIME type at all.

Usage:
    python migrate_add_user_columns.py
"""

from __future__ import annotations

from sqlalchemy import inspect

from app.db.migration_utils import add_column, boolean_false_literal, column_exists
from app.db.session import engine

TABLE = "users"

# column -> what follows the type in the ALTER statement. The profile
# fields are nullable because they genuinely are optional; the flag is NOT
# NULL with a false default so existing rows are backfilled in the same
# statement, granting nobody protection they did not have.
COLUMNS: dict[str, str] = {
    "full_name": "NULL",
    "email": "NULL",
    "is_system_admin": None,  # resolved below: needs the dialect's literal
}


def main() -> int:
    if TABLE not in inspect(engine).get_table_names():
        # A brand-new database has no users table yet; init_db.py will
        # create it from the model with every column included.
        print(f"Table '{TABLE}' does not exist yet -- nothing to migrate.")
        return 0

    suffixes = dict(COLUMNS)
    suffixes["is_system_admin"] = f"NOT NULL DEFAULT {boolean_false_literal(engine)}"

    added = 0
    skipped = 0
    for column, suffix in suffixes.items():
        if add_column(engine, TABLE, column, suffix=suffix):
            print(f"  added {TABLE}.{column}")
            added += 1
        else:
            skipped += 1

    # Re-inspect rather than trusting the statements: a silently ignored
    # ALTER would otherwise look like success.
    missing = [c for c in suffixes if not column_exists(engine, TABLE, c)]
    if missing:
        print(f"FAILED: still missing {', '.join(f'{TABLE}.{c}' for c in missing)}")
        return 1

    print(f"User columns: {added} added, {skipped} already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
