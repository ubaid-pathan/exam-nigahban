"""Migration: add the voiding columns to monitoring_events and exams.

Voiding is how a record stops having effect without being destroyed: it is
hidden from every queue, count and report, but survives with who voided it,
when, and why. See app/api/routes/void.py.

create_all cannot add columns to tables that already exist, so these six
columns have to be added explicitly or every query selecting them fails --
SQLAlchemy names each mapped column in its SELECT, so an absent column
breaks reads of the whole table, not just the new field.

Idempotent and portable across SQLite, MySQL and PostgreSQL: each column is
checked against the live schema first, and its type is compiled from the
model for the connected dialect rather than hard-coded (see
app/db/migration_utils.py -- DATETIME is not a PostgreSQL type at all).

Foreign keys are deliberately not declared in the ALTER statements. SQLite
cannot add a constrained column to an existing table, and the constraint
adds nothing the application does not already enforce -- the column is only
ever set to the id of the authenticated system administrator performing the
void.

Usage:
    python migrate_add_void_columns.py
"""

from __future__ import annotations

from sqlalchemy import inspect

from app.db.migration_utils import add_column, column_exists
from app.db.session import engine

COLUMNS: dict[str, tuple[str, ...]] = {
    "monitoring_events": ("voided_at", "voided_by_admin_id", "void_reason"),
    "exams": ("voided_at", "voided_by_admin_id", "void_reason"),
}


def main() -> int:
    existing_tables = set(inspect(engine).get_table_names())

    added = 0
    skipped = 0

    for table, columns in COLUMNS.items():
        if table not in existing_tables:
            # A brand-new database has no such table yet; init_db.py will
            # create it from the model with these columns included.
            print(f"Table '{table}' does not exist yet -- nothing to migrate.")
            continue

        for column in columns:
            if add_column(engine, table, column, suffix="NULL"):
                print(f"  added {table}.{column}")
                added += 1
            else:
                skipped += 1

    # Re-inspect rather than trusting the statements: a silently ignored
    # ALTER would otherwise look like success.
    missing = [
        f"{table}.{column}"
        for table, columns in COLUMNS.items()
        if table in set(inspect(engine).get_table_names())
        for column in columns
        if not column_exists(engine, table, column)
    ]
    if missing:
        print(f"FAILED: still missing {', '.join(missing)}")
        return 1

    print(f"Void columns: {added} added, {skipped} already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
