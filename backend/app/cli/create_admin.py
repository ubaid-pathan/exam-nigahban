"""One-time CLI bootstrap for the very first administrator account.

Why this exists
----------------
`POST /api/users/admins` (see app/api/routes/users.py) is intentionally
protected by `require_admin` -- only an existing admin can create another
one. That's correct for ongoing account management, but it means a fresh
deployment with an empty `users` table has no way to create *any* admin
through the application itself. This command closes that gap with a
narrowly-scoped, interactive, local-only tool: it never becomes an API
endpoint, and it refuses to run at all once any admin account (active or
inactive) exists.

Usage
-----
    python -m app.cli.create_admin

Run this exactly once, immediately after the database schema has been
created and before any admin account exists. It will prompt for a
username and password (input is not echoed), confirm the password, and
create the account with role="admin" and status=True.

Once the first admin exists, use the authenticated
`POST /api/users/admins` endpoint (logged in as that admin) for every
admin account after that -- this command will refuse to run again.
"""

from __future__ import annotations

import getpass
import sys

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal
from app.schemas.user import AdminCreateRequest

MAX_USERNAME_LENGTH = 50  # matches the users.username column: String(50)


class BootstrapError(Exception):
    """Raised when the first-admin bootstrap cannot proceed."""


def admin_exists(db: Session) -> bool:
    """True if any admin account exists, active or inactive."""
    return db.query(User).filter(User.role == "admin").first() is not None


def _validate_credentials(
    username: str, password: str, confirm_password: str
) -> AdminCreateRequest:
    stripped_username = username.strip() if username else ""
    if not stripped_username:
        raise BootstrapError("Username must not be empty.")
    if len(stripped_username) > MAX_USERNAME_LENGTH:
        raise BootstrapError(
            f"Username must be at most {MAX_USERNAME_LENGTH} characters."
        )
    if not password:
        raise BootstrapError("Password must not be empty.")
    if password != confirm_password:
        raise BootstrapError("Password and confirmation do not match.")

    try:
        # Reuses the same schema the authenticated admin-creation endpoint
        # validates against, so this command never drifts from those
        # conventions as they evolve.
        return AdminCreateRequest(username=stripped_username, password=password)
    except PydanticValidationError as exc:
        raise BootstrapError(f"Invalid admin credentials: {exc}") from None


def bootstrap_admin(
    db: Session, username: str, password: str, confirm_password: str
) -> User:
    """Create the first admin account, or raise BootstrapError.

    Refuses if any admin already exists, if the username is taken, or if
    the credentials fail validation. Commits only after every check
    passes; rolls back and leaves no partial row on any database failure.
    """
    payload = _validate_credentials(username, password, confirm_password)

    if admin_exists(db):
        raise BootstrapError(
            "An administrator account already exists. This command only "
            "provisions the very first admin; use the authenticated "
            "POST /api/users/admins endpoint (as an existing admin) to "
            "create additional admin accounts."
        )

    if db.query(User).filter(User.username == payload.username).first():
        raise BootstrapError(f"Username '{payload.username}' already exists.")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="admin",
        status=True,
    )
    db.add(user)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise BootstrapError(
            f"Could not create admin account '{payload.username}': the "
            "username may already be in use, or a database error occurred."
        ) from None

    db.refresh(user)
    return user


def main() -> int:
    db = SessionLocal()
    try:
        if admin_exists(db):
            print(
                "An administrator account already exists. This bootstrap "
                "command only provisions the very first admin. Use the "
                "authenticated POST /api/users/admins endpoint (logged in "
                "as an existing admin) to create additional admin accounts."
            )
            return 1

        print("Exam Nigahban -- First Administrator Bootstrap")
        print(
            "This creates the initial administrator account. Run it once, "
            "before any admin account exists.\n"
        )

        username = input("Admin username: ")
        password = getpass.getpass("Admin password: ")
        confirm_password = getpass.getpass("Confirm password: ")

        try:
            user = bootstrap_admin(db, username, password, confirm_password)
        except BootstrapError as exc:
            print(f"\nCould not create admin account: {exc}")
            return 1

        print(f"\nAdministrator account '{user.username}' created successfully.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
