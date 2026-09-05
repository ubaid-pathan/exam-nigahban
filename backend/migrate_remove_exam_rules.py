"""One-time migration: remove per-exam monitoring-rule overrides.

The monitoring-rules feature originally supported two layers: global default
rules (exam_id IS NULL) and optional per-exam overrides (exam_id set).  The
per-exam customization layer has been removed from the application; this
migration aligns the database with the simplified MonitoringRule model:

  1. Deletes exam-specific rule rows (exam_id IS NOT NULL).
  2. Drops the monitoring_rules.exam_id column together with its foreign
     key and the (exam_id, event_type) unique constraint.
  3. Adds a unique constraint on event_type alone.
  4. Drops the now-redundant plain index on event_type, so a migrated
     database matches one created fresh by init_db.py.

Idempotent and dialect-agnostic (MySQL and PostgreSQL): every step inspects
the live schema first, so re-running against an already-migrated database
is a no-op.

Usage:
    python migrate_remove_exam_rules.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.db.session import engine

TABLE = "monitoring_rules"
REMOVED_COLUMN = "exam_id"
OLD_UNIQUE_COLUMNS = ["exam_id", "event_type"]
NEW_UNIQUE = "uq_monitoring_rule_event_type"
NEW_UNIQUE_COLUMNS = ["event_type"]


def _quote(identifier: str) -> str:
    if engine.dialect.name == "mysql":
        return f"`{identifier}`"
    return f'"{identifier}"'


def _run(statement: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(statement))


def _column_names(entry: dict) -> list[str]:
    return list(entry.get("column_names") or [])


def _matches(entry_columns: list[str], columns: list[str]) -> bool:
    return sorted(entry_columns) == sorted(columns)


def _has_exam_id_column(inspector) -> bool:
    return any(col["name"] == REMOVED_COLUMN for col in inspector.get_columns(TABLE))


def _fk_name(inspector) -> str | None:
    """Name of the foreign key covering the removed column, if any."""
    for fk in inspector.get_foreign_keys(TABLE):
        if REMOVED_COLUMN in (fk.get("constrained_columns") or []):
            return fk.get("name")
    return None


def _unique_names(inspector, columns: list[str]) -> list[str]:
    """Names of unique indexes/constraints whose columns exactly match.

    MySQL materialises unique constraints as unique indexes; PostgreSQL
    exposes them separately.  Both views are checked and de-duplicated.
    """
    names: list[str] = []
    for index in inspector.get_indexes(TABLE):
        if index.get("unique") and _matches(_column_names(index), columns) and index.get("name"):
            names.append(index["name"])
    for constraint in inspector.get_unique_constraints(TABLE):
        if _matches(_column_names(constraint), columns) and constraint.get("name"):
            names.append(constraint["name"])
    return list(dict.fromkeys(names))


def _plain_index_names_on(inspector, columns: list[str]) -> list[str]:
    """Names of non-unique indexes whose columns exactly match.

    Names vary between databases (ix_... vs idx_...), so plain indexes are
    matched by their columns instead.
    """
    return [
        index["name"]
        for index in inspector.get_indexes(TABLE)
        if not index.get("unique")
        and index.get("name")
        and _matches(_column_names(index), columns)
    ]


def _delete_override_rows() -> int:
    with engine.begin() as conn:
        count = conn.execute(
            text(
                f"SELECT COUNT(*) FROM {_quote(TABLE)} "
                f"WHERE {_quote(REMOVED_COLUMN)} IS NOT NULL"
            )
        ).scalar_one()
        if count:
            conn.execute(
                text(
                    f"DELETE FROM {_quote(TABLE)} "
                    f"WHERE {_quote(REMOVED_COLUMN)} IS NOT NULL"
                )
            )
    return count


def main() -> int:
    inspector = inspect(engine)

    if TABLE not in inspector.get_table_names():
        print(f"Table '{TABLE}' does not exist; nothing to migrate.")
        return 0

    if _has_exam_id_column(inspector):
        deleted = _delete_override_rows()
        print(f"Deleted {deleted} exam-specific rule row(s).")

        fk_name = _fk_name(inspector)
        if fk_name:
            if engine.dialect.name == "mysql":
                _run(f"ALTER TABLE {_quote(TABLE)} DROP FOREIGN KEY {_quote(fk_name)}")
            else:
                _run(f"ALTER TABLE {_quote(TABLE)} DROP CONSTRAINT {_quote(fk_name)}")
            print(f"Dropped foreign key '{fk_name}' on {REMOVED_COLUMN}.")
        else:
            print(
                "Warning: no foreign key name was reflected for "
                f"{REMOVED_COLUMN}; column drop may fail if one exists."
            )

        for name in _unique_names(inspector, OLD_UNIQUE_COLUMNS):
            if engine.dialect.name == "mysql":
                _run(f"ALTER TABLE {_quote(TABLE)} DROP INDEX {_quote(name)}")
            else:
                _run(f"ALTER TABLE {_quote(TABLE)} DROP CONSTRAINT {_quote(name)}")
            print(f"Dropped unique constraint '{name}' on {OLD_UNIQUE_COLUMNS}.")

        _run(f"ALTER TABLE {_quote(TABLE)} DROP COLUMN {_quote(REMOVED_COLUMN)}")
        print(f"Dropped column '{TABLE}.{REMOVED_COLUMN}'.")

        # The DDL above changed the schema; re-inspect before the checks below.
        inspector = inspect(engine)
    else:
        print(f"Column '{TABLE}.{REMOVED_COLUMN}' already absent; skipping cleanup.")

    if not _unique_names(inspector, NEW_UNIQUE_COLUMNS):
        if engine.dialect.name == "mysql":
            _run(
                f"ALTER TABLE {_quote(TABLE)} "
                f"ADD UNIQUE INDEX {_quote(NEW_UNIQUE)} ({_quote('event_type')})"
            )
        else:
            _run(
                f"ALTER TABLE {_quote(TABLE)} "
                f"ADD CONSTRAINT {_quote(NEW_UNIQUE)} UNIQUE ({_quote('event_type')})"
            )
        print(f"Added unique constraint '{NEW_UNIQUE}' on event_type.")

    for name in _plain_index_names_on(inspector, NEW_UNIQUE_COLUMNS):
        if engine.dialect.name == "mysql":
            _run(f"ALTER TABLE {_quote(TABLE)} DROP INDEX {_quote(name)}")
        else:
            _run(f"DROP INDEX {_quote(name)}")
        print(f"Dropped redundant plain index '{name}' on {NEW_UNIQUE_COLUMNS}.")

    with engine.begin() as conn:
        remaining = conn.execute(
            text(f"SELECT COUNT(*) FROM {_quote(TABLE)}")
        ).scalar_one()
    print(f"Migration complete: {remaining} global rule row(s) remain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
