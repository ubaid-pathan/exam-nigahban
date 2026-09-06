"""Step-up authentication for privileged destructive actions.

An admin session is enough to review evidence. It is not enough to void a
monitoring event or an exam: those actions remove records from every queue
and report, so they require the acting administrator to re-enter their own
password at the moment of the action. A stolen or unattended session
cannot perform them.

Verifying a password on demand also creates an oracle -- an endpoint that
answers "is this the right password?" as often as it is asked. This module
therefore pairs verification with attempt limiting, so a caller holding a
session cannot use the void endpoint to test passwords at will.

Limitations, stated because they matter for how far this can be trusted:
the counters live in this process's memory, so they reset when the API
restarts and are not shared between workers. That is sufficient for a
single-worker deployment and is a real weakness at higher concurrency,
where this belongs in the database or a shared cache.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.security import verify_password

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


@dataclass
class _AttemptRecord:
    failures: int = 0
    locked_until: datetime | None = field(default=None)


class StepUpLockedError(Exception):
    """Raised when too many failed confirmations have been made.

    Carries the remaining lockout so the caller can tell the user when to
    try again rather than leaving them guessing.
    """

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            "Too many incorrect password confirmations. "
            f"Try again in {retry_after_seconds} seconds."
        )


class StepUpVerifier:
    """Verifies a re-entered password and rate-limits failures per user."""

    def __init__(self) -> None:
        self._attempts: dict[int, _AttemptRecord] = {}

    def _record(self, user_id: int) -> _AttemptRecord:
        return self._attempts.setdefault(user_id, _AttemptRecord())

    def check_not_locked(self, user_id: int) -> None:
        """Raises StepUpLockedError if this user is currently locked out.

        Called before the password is even compared, so a locked-out caller
        learns nothing from the timing or the result.
        """
        record = self._record(user_id)
        if record.locked_until is None:
            return
        now = datetime.utcnow()
        if record.locked_until <= now:
            # The lockout has elapsed; clear it and let the attempt through
            # with a fresh count.
            record.failures = 0
            record.locked_until = None
            return
        raise StepUpLockedError(int((record.locked_until - now).total_seconds()) + 1)

    def verify(self, user_id: int, password: str, password_hash: str) -> bool:
        """True when the password matches. Never logs or returns it.

        A success clears the failure count; a failure that reaches the limit
        starts a lockout. The caller must have called check_not_locked first.
        """
        if verify_password(password, password_hash):
            self._attempts.pop(user_id, None)
            return True

        record = self._record(user_id)
        record.failures += 1
        if record.failures >= MAX_FAILED_ATTEMPTS:
            record.locked_until = datetime.utcnow() + LOCKOUT_DURATION
            # A security-relevant event worth recording. The password
            # itself is never included, here or anywhere else.
            logger.warning(
                "Step-up confirmation locked for user %s after %s failed attempts",
                user_id,
                record.failures,
            )
        return False

    def reset(self, user_id: int | None = None) -> None:
        """Clears recorded failures. Used by tests; `None` clears all."""
        if user_id is None:
            self._attempts.clear()
        else:
            self._attempts.pop(user_id, None)


step_up_verifier = StepUpVerifier()
