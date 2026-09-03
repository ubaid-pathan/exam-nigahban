from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

import pytest

import app.cli.create_admin as create_admin_module
from app.cli.create_admin import (
    MAX_USERNAME_LENGTH,
    BootstrapError,
    admin_exists,
    bootstrap_admin,
    main,
)
from app.core.security import verify_password
from app.db.models import User


def _make_inactive_admin(db_session) -> User:
    admin = User(
        username="dormant_admin",
        password_hash="irrelevant-hash",
        role="admin",
        status=False,
    )
    db_session.add(admin)
    db_session.commit()
    return admin


# --- bootstrap_admin: core behavior -----------------------------------


def test_first_admin_can_be_created(db_session):
    user = bootstrap_admin(db_session, "firstadmin", "supersecret123", "supersecret123")

    assert user.id is not None
    assert db_session.query(User).count() == 1


def test_created_account_has_admin_role(db_session):
    user = bootstrap_admin(db_session, "firstadmin", "supersecret123", "supersecret123")

    assert user.role == "admin"


def test_created_account_is_active(db_session):
    user = bootstrap_admin(db_session, "firstadmin", "supersecret123", "supersecret123")

    assert user.status is True


def test_password_is_stored_as_hash_never_plaintext(db_session):
    user = bootstrap_admin(db_session, "firstadmin", "supersecret123", "supersecret123")

    assert user.password_hash != "supersecret123"
    assert verify_password("supersecret123", user.password_hash)


def test_admin_exists_detects_admin_regardless_of_status(db_session):
    assert admin_exists(db_session) is False

    _make_inactive_admin(db_session)

    assert admin_exists(db_session) is True


# --- refusal when an admin already exists ------------------------------


def test_bootstrap_refuses_when_active_admin_already_exists(db_session, admin_user):
    with pytest.raises(BootstrapError, match="already exists"):
        bootstrap_admin(db_session, "anotheradmin", "supersecret123", "supersecret123")

    assert db_session.query(User).filter(User.role == "admin").count() == 1


def test_bootstrap_refuses_when_inactive_admin_already_exists(db_session):
    _make_inactive_admin(db_session)

    with pytest.raises(BootstrapError, match="already exists"):
        bootstrap_admin(db_session, "newadmin", "supersecret123", "supersecret123")


def test_existing_admin_account_is_never_modified(db_session, admin_user):
    original_hash = admin_user.password_hash
    original_username = admin_user.username

    with pytest.raises(BootstrapError):
        bootstrap_admin(db_session, "someoneelse", "supersecret123", "supersecret123")

    db_session.refresh(admin_user)
    assert admin_user.password_hash == original_hash
    assert admin_user.username == original_username
    assert admin_user.role == "admin"
    assert admin_user.status is True


# --- input validation ----------------------------------------------------


def test_duplicate_username_is_rejected(db_session, student_user):
    with pytest.raises(BootstrapError, match="already exists"):
        bootstrap_admin(
            db_session, student_user.username, "supersecret123", "supersecret123"
        )


def test_password_confirmation_mismatch_is_rejected(db_session):
    with pytest.raises(BootstrapError, match="do not match"):
        bootstrap_admin(db_session, "firstadmin", "supersecret123", "different456")

    assert db_session.query(User).count() == 0


def test_empty_username_is_rejected(db_session):
    with pytest.raises(BootstrapError, match="Username must not be empty"):
        bootstrap_admin(db_session, "   ", "supersecret123", "supersecret123")

    assert db_session.query(User).count() == 0


def test_empty_password_is_rejected(db_session):
    with pytest.raises(BootstrapError, match="Password must not be empty"):
        bootstrap_admin(db_session, "firstadmin", "", "")

    assert db_session.query(User).count() == 0


def test_username_exceeding_max_length_is_rejected(db_session):
    too_long_username = "a" * (MAX_USERNAME_LENGTH + 1)

    with pytest.raises(BootstrapError, match="at most"):
        bootstrap_admin(db_session, too_long_username, "supersecret123", "supersecret123")


# --- database failure handling ------------------------------------------


def test_database_failure_does_not_leave_partial_user(db_session, monkeypatch):
    def _raise_on_commit():
        raise SQLAlchemyError("simulated database failure")

    monkeypatch.setattr(db_session, "commit", _raise_on_commit)

    with pytest.raises(BootstrapError, match="Could not create admin account"):
        bootstrap_admin(db_session, "firstadmin", "supersecret123", "supersecret123")

    assert db_session.query(User).filter(User.username == "firstadmin").first() is None


# --- CLI entrypoint (app.cli.create_admin.main) --------------------------


def test_main_blocks_before_any_prompt_when_admin_exists(
    db_session, admin_user, monkeypatch, capsys
):
    test_session_local = sessionmaker(bind=db_session.get_bind())
    monkeypatch.setattr(create_admin_module, "SessionLocal", test_session_local)
    # No input()/getpass.getpass() patch is installed: if main() reached a
    # prompt before returning, it would raise (no interactive stdin under
    # pytest), so a clean return here proves the early-exit ran first.

    exit_code = main()

    assert exit_code == 1
    assert "already exists" in capsys.readouterr().out.lower()


def test_main_creates_first_admin_via_prompts(db_session, monkeypatch, capsys):
    test_session_local = sessionmaker(bind=db_session.get_bind())
    monkeypatch.setattr(create_admin_module, "SessionLocal", test_session_local)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "cli_admin")
    passwords = iter(["supersecret123", "supersecret123"])
    monkeypatch.setattr("getpass.getpass", lambda _prompt="": next(passwords))

    exit_code = main()

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "created successfully" in output.lower()
    assert "supersecret123" not in output

    created = db_session.query(User).filter(User.username == "cli_admin").first()
    assert created is not None
    assert created.role == "admin"
    assert created.status is True
    assert created.password_hash != "supersecret123"
