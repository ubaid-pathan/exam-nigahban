"""Designate the protected system administrator account.

Why this is a CLI and not an API endpoint
-----------------------------------------
The system administrator is the account that cannot be deactivated by
anyone, including itself -- it is what guarantees the system always retains
a way in. An account with that property must not be creatable over HTTP,
because then it would be exactly as strong as the weakest admin session:
anyone who compromised any admin could mint an account no one else can
disable, and lock the real owners out of their own system.

Running here instead means designation requires access to the server or the
database itself, which is a materially higher bar.

What it does
------------
Either creates a new admin account carrying the flag, or promotes an
existing admin to it. Refuses if a system administrator already exists --
there is exactly one, and replacing it is a deliberate act that should be
done knowingly rather than by re-running a bootstrap command.

Usage:
    python -m app.cli.create_system_admin
"""

from __future__ import annotations

import getpass
import sys

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal

MIN_PASSWORD_LENGTH = 8
MAX_USERNAME_LENGTH = 50  # matches users.username: String(50)


class SystemAdminError(Exception):
    """Raised when the designation cannot proceed."""


def existing_system_admin(db: Session) -> User | None:
    return db.query(User).filter(User.is_system_admin.is_(True)).first()


def promote(db: Session, username: str) -> User:
    """Marks an existing admin as the system administrator.

    Reactivates the account as a side effect: designating a deactivated
    account as the one that can never be deactivated would leave the
    system with a protected account nobody can log into.
    """
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise SystemAdminError(f"No account named '{username}' exists.")
    if user.role != "admin":
        raise SystemAdminError(
            f"'{username}' is a {user.role} account. Only an administrator "
            "can be designated system administrator."
        )

    user.is_system_admin = True
    user.status = True
    db.commit()
    db.refresh(user)
    return user


def create(db: Session, username: str, password: str, full_name: str | None) -> User:
    if db.query(User).filter(User.username == username).first() is not None:
        raise SystemAdminError(
            f"An account named '{username}' already exists. Promote it "
            "instead of creating a new one."
        )

    user = User(
        username=username,
        password_hash=hash_password(password),
        role="admin",
        status=True,
        full_name=full_name or None,
        is_system_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _prompt_password() -> str:
    password = getpass.getpass("Password (input hidden): ")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemAdminError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if password != getpass.getpass("Confirm password: "):
        raise SystemAdminError("Passwords did not match.")
    return password


def main() -> int:
    db = SessionLocal()
    try:
        current = existing_system_admin(db)
        if current is not None:
            print(
                f"A system administrator already exists: '{current.username}'.\n"
                "There is exactly one. To move the designation, clear the flag "
                "on that account directly first -- this command will not "
                "reassign it silently."
            )
            return 1

        admin_count = db.query(User).filter(User.role == "admin").count()
        print(f"Existing administrator accounts: {admin_count}")
        print()
        print("  1) Create a new account as system administrator")
        print("  2) Promote an existing administrator")
        choice = input("Choose 1 or 2: ").strip()

        if choice == "2":
            username = input("Existing administrator username: ").strip()
            user = promote(db, username)
        elif choice == "1":
            username = input("New username: ").strip()
            if not username:
                raise SystemAdminError("Username must not be empty.")
            if len(username) > MAX_USERNAME_LENGTH:
                raise SystemAdminError(
                    f"Username must be at most {MAX_USERNAME_LENGTH} characters."
                )
            full_name = input("Full name (optional): ").strip()
            user = create(db, username, _prompt_password(), full_name)
        else:
            raise SystemAdminError("Choose 1 or 2.")

        print()
        print(f"'{user.username}' is now the system administrator.")
        print("It cannot be deactivated by anyone, including itself.")
        print()
        print(
            "Next: sign in as this account and deactivate the administrators "
            "you are retiring. Deactivating -- rather than deleting -- keeps "
            "their past review decisions attributable, which is what makes "
            "the audit trail defensible."
        )
        return 0

    except SystemAdminError as exc:
        print(f"Error: {exc}")
        return 1
    except SQLAlchemyError as exc:
        db.rollback()
        print(f"Database error: {exc}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
