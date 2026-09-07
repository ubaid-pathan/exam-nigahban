"""Structured application logging.

Why structured
--------------
A line written for a human reading a terminal ("Admin confirmed event 412")
answers a question only if you already know which line to look for. This
system's operational questions are the other shape: "show me everything
that happened in session 51", "which accounts had failed logins tonight".
Those are filters over fields, so every event is emitted as one JSON object
with named fields rather than an interpolated sentence.

What this is NOT
----------------
Not a second audit trail. admin_actions and enforcement_actions are the
authoritative record of decisions -- in the database, queryable, and shown
in the reports. Duplicating them here would be noise. These logs carry the
operational events that never become rows: who signed in, which sessions
started, when a socket dropped, when a step-up lockout fired.

Never logged
------------
Passwords, tokens, secret keys, credentials -- never, under any
condition. The
helper below takes named fields, so a caller has to go out of its way to
pass one -- and tests/test_logging.py asserts none appear.

Output goes to stdout only. Render and comparable hosts capture stdout
automatically, so there is no file handling, no rotation, and no new
dependency.
"""

from __future__ import annotations

import json
import logging
import logging.config
import os
import sys
from datetime import datetime, timezone
from typing import Any

# The logger every application event goes through. Named so that host-level
# log filtering can separate deliberate events from framework chatter.
EVENT_LOGGER = "exam_nigahban.events"

# Fields the standard library puts on every LogRecord. Anything outside
# this set was added by a caller and belongs in the JSON output.
_RESERVED = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
) | {"asctime", "message", "taskName"}


class JsonFormatter(logging.Formatter):
    """Renders a record as a single JSON object.

    Any extra passed to the logging call becomes a top-level field, so an
    event's own data is queryable rather than embedded in prose.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # default=str so an unexpected value (a datetime, a Decimal) is
        # rendered rather than raising inside the logging call and losing
        # the event entirely.
        return json.dumps(payload, default=str)


def configure_logging(level: str | None = None) -> None:
    """Installs the JSON handler. Safe to call more than once.

    `disable_existing_loggers` is False so the module-level loggers already
    created across the application keep working and are picked up by this
    configuration rather than silenced by it.
    """
    resolved = (level or os.environ.get("LOG_LEVEL") or "INFO").upper()

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"json": {"()": JsonFormatter}},
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": sys.stdout,
                }
            },
            "root": {"handlers": ["stdout"], "level": resolved},
            "loggers": {
                # Uvicorn installs its own handlers; routing them here keeps
                # one format across the whole stream. propagate=False stops
                # each line being emitted twice.
                "uvicorn": {"handlers": ["stdout"], "level": resolved, "propagate": False},
                "uvicorn.error": {
                    "handlers": ["stdout"],
                    "level": resolved,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["stdout"],
                    "level": resolved,
                    "propagate": False,
                },
            },
        }
    )


def log_event(event: str, /, level: int = logging.INFO, **fields: Any) -> None:
    """Records one named application event with structured fields.

    Call sites read as events rather than sentences:

        log_event("auth.login.failed", username=username)

    `event` is a dotted name so related events group under a prefix
    (auth.*, exam.*, monitoring.*), which is what makes the stream
    filterable.

    Never pass a password, token or key. The signature takes named fields
    precisely so that doing it would be a deliberate act, and
    tests/test_logging.py asserts that none appear in the output.
    """
    logging.getLogger(EVENT_LOGGER).log(level, event, extra={"event": event, **fields})
