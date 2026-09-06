"""Report whether the connected database matches the current models.

Why this exists
---------------
init_db.py calls Base.metadata.create_all, which creates MISSING TABLES but
never adds MISSING COLUMNS to a table that already exists. Any column added
to an existing model after a database was first created therefore has to be
applied by hand -- and nothing in the deploy pipeline will tell you it is
absent. The first symptom is a 500 on whatever query selects it.

Run this against a deployed database (e.g. from the Render Shell, where the
production environment variables are already set) before and after a deploy
that changes any model:

    python check_schema.py

Exits 0 when the database has everything the models expect, 1 otherwise, so
it can also be used as a deploy gate.

Read-only: it inspects the schema and changes nothing.
"""

from __future__ import annotations

import sys

from sqlalchemy import inspect

from app.db.base import Base
from app.db.session import engine

# Importing the models package registers every table on Base.metadata --
# without it the comparison below would find nothing to check.
import app.db.models  # noqa: F401


def main() -> int:
    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables)

    print(f"Dialect: {engine.dialect.name}")
    print(f"Tables expected by the models: {len(expected_tables)}")
    print(f"Tables present in the database: {len(actual_tables)}")
    print()

    missing_tables = sorted(expected_tables - actual_tables)
    missing_columns: list[str] = []

    for table_name in sorted(expected_tables & actual_tables):
        expected_columns = set(Base.metadata.tables[table_name].columns.keys())
        actual_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        for column in sorted(expected_columns - actual_columns):
            missing_columns.append(f"{table_name}.{column}")

    if missing_tables:
        print("MISSING TABLES (create_all will add these on next deploy):")
        for name in missing_tables:
            print(f"  - {name}")
        print()

    if missing_columns:
        print("MISSING COLUMNS (create_all will NOT add these -- migrate by hand):")
        for name in missing_columns:
            print(f"  - {name}")
        print()

    extra_tables = sorted(actual_tables - expected_tables)
    if extra_tables:
        # Not a failure: a table the models no longer describe is usually a
        # leftover from a removed feature, harmless but worth seeing.
        print(f"Tables in the database that no model describes: {extra_tables}")
        print()

    if missing_tables or missing_columns:
        print("RESULT: schema is BEHIND the models.")
        return 1

    print("RESULT: schema matches the models.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
