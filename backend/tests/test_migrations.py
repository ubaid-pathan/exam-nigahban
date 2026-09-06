"""Tests for the ADD COLUMN migrations.

These exist because a migration is the one piece of code whose failure
mode is "the deploy stops". build.sh runs with `set -o errexit`, so a
single invalid ALTER aborts the release before the application ever
starts.

The specific danger is dialect drift: the suite runs on SQLite, local
development uses MySQL, and deployment is PostgreSQL. Hand-written DDL
that works on two of the three passes every local check and then breaks
production. Two real examples, both of which shipped before being caught:

  * DATETIME is not a PostgreSQL type -- it wants TIMESTAMP WITHOUT TIME ZONE
  * BOOLEAN ... DEFAULT 0 is rejected by PostgreSQL, which will not take a
    bare integer as a boolean literal

so these tests assert the emitted SQL is right for each dialect, not just
that it happens to run here.
"""

import pytest
from sqlalchemy.dialects import mysql, postgresql, sqlite

from app.db.migration_utils import boolean_false_literal, column_type_sql


class _FakeEngine:
    """Carries just the `dialect` attribute the helpers read."""

    def __init__(self, dialect):
        self.dialect = dialect


DIALECTS = {
    "postgresql": postgresql.dialect(),
    "mysql": mysql.dialect(),
    "sqlite": sqlite.dialect(),
}


@pytest.fixture(params=sorted(DIALECTS))
def dialect_name(request):
    return request.param


@pytest.fixture
def engine_for(dialect_name):
    return _FakeEngine(DIALECTS[dialect_name])


# ---------------------------------------------------------------------------
# Column types must come from the dialect, not from a hand-written string
# ---------------------------------------------------------------------------


def test_datetime_columns_never_emit_the_literal_datetime_on_postgres():
    """The bug that would have aborted a Postgres deploy."""
    sql = column_type_sql("monitoring_events", "voided_at", _FakeEngine(DIALECTS["postgresql"]))

    assert "TIMESTAMP" in sql.upper()
    assert sql.upper() != "DATETIME"


def test_datetime_columns_still_emit_datetime_on_mysql_and_sqlite():
    for name in ("mysql", "sqlite"):
        sql = column_type_sql("monitoring_events", "voided_at", _FakeEngine(DIALECTS[name]))
        assert sql.upper() == "DATETIME", f"{name} produced {sql}"


def test_boolean_default_is_a_real_boolean_on_postgres():
    """PostgreSQL rejects `DEFAULT 0` for a boolean column."""
    assert boolean_false_literal(_FakeEngine(DIALECTS["postgresql"])) == "false"


def test_boolean_default_is_zero_on_mysql_and_sqlite():
    for name in ("mysql", "sqlite"):
        assert boolean_false_literal(_FakeEngine(DIALECTS[name])) == "0"


def test_every_migrated_column_compiles_for_every_supported_dialect(engine_for):
    """No migrated column may produce empty or obviously wrong DDL on any
    engine this project supports."""
    migrated = [
        ("users", "is_system_admin"),
        ("monitoring_events", "voided_at"),
        ("monitoring_events", "voided_by_admin_id"),
        ("monitoring_events", "void_reason"),
        ("exams", "voided_at"),
        ("exams", "voided_by_admin_id"),
        ("exams", "void_reason"),
    ]
    for table, column in migrated:
        sql = column_type_sql(table, column, engine_for)
        assert sql and sql.strip(), f"{table}.{column} produced no type"


def test_text_and_integer_columns_are_spelled_the_same_everywhere(engine_for):
    """Sanity check on the assumption that only DATETIME and BOOLEAN
    actually differ between these three engines."""
    assert column_type_sql("monitoring_events", "void_reason", engine_for).upper() == "TEXT"
    assert (
        column_type_sql("monitoring_events", "voided_by_admin_id", engine_for).upper()
        == "INTEGER"
    )


# ---------------------------------------------------------------------------
# The helpers are driven by the models, so they cannot drift from them
# ---------------------------------------------------------------------------


def test_an_unmapped_column_is_a_hard_error_not_a_silent_guess(engine_for):
    """Deriving DDL from the model means a typo fails loudly here rather
    than emitting plausible-looking SQL for a column that does not exist."""
    with pytest.raises(KeyError):
        column_type_sql("users", "no_such_column", engine_for)
