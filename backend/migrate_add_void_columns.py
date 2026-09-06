"""Migration: add the voiding columns to monitoring_events and exams.

Voiding is how a record stops having effect without being destroyed: it is
hidden from every queue, count and report, but survives with who voided it,
when, and why. See app/api/routes/void.py.

create_all cannot add columns to tables that already exist, so these six
columns have to be added explicitly or every query selecting them fails --
SQLAlchemy names each mapped column in its SELECT, so an absent column
breaks reads of the whole table, not just the new field.

Idempotent and dialect-agnostic (SQLite, MySQL, PostgreSQL): each column is
checked against the live schema first, so re-running is a no-op and a
partially applied migration finishes cleanly.

Foreign keys are deliberately NOT declared in the ALTER statements. SQLite
cannot add a constrained column to an existing table, and the constraint
adds nothing here that the application does not already enforce -- the
column is only ever set to the id of the authenticated system administrator
performing the void.

Usage:
    python migrate_add_void_columns.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.db.session import engine

# table -> column -> SQL type. TEXT/DATETIME/INTEGER are spelled the same
# way by all three supported engines.
COLUMNS: dict[str, dict[str, str]] = {
    "monitoring_events": {
        "voided_at": "DATETIME NULL",
        "voided_by_admin_id": "INTEGER NULL",
        "void_reason": "TEXT NULL",
    },
    "exams": {
        "voided_at": "DATETIME NULL",
        "voided_by_admin_id": "INTEGER NULL",
        "void_reason": "TEXT NULL",
    },
}


def main() -> int:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    added = 0
    skipped = 0

    for table, columns in COLUMNS.items():
        if table not in existing_tables:
            # A brand-new database has no such table yet; init_db.py will
            # create it from the model with these columns included.
            print(f"Table '{table}' does not exist yet -- nothing to migrate.")
            continue

        present = {col["name"] for col in inspector.get_columns(table)}

        for column, sql_type in columns.items():
            if column in present:
                skipped += 1
                continue
            with engine.begin() as connection:
                connection.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
                )
            print(f"  added {table}.{column}")
            added += 1

    # Re-inspect rather than trusting the statements: a silently ignored
    # ALTER would otherwise look like success.
    verifier = inspect(engine)
    missing = [
        f"{table}.{column}"
        for table, columns in COLUMNS.items()
        if table in set(verifier.get_table_names())
        for column in columns
        if column not in {c["name"] for c in verifier.get_columns(table)}
    ]
    if missing:
        print(f"FAILED: still missing {', '.join(missing)}")
        return 1

    print(f"Void columns: {added} added, {skipped} already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
