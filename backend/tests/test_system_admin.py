"""Tests for the protected system administrator account.

The account exists to guarantee the system always retains a way in, so the
property that matters is negative and absolute: nothing may deactivate it.
Not another administrator, not itself, and not the last-admin rule that
governs every other account.
"""

import pytest

from app.cli.create_system_admin import (
    SystemAdminError,
    create,
    existing_system_admin,
    promote,
)
from app.core.security import hash_password
from app.db.models import User


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def system_admin(db_session):
    user = User(
        username="sysadmin",
        password_hash=hash_password("sysadminpass123"),
        role="admin",
        status=True,
        is_system_admin=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def second_admin(db_session):
    user = User(
        username="admin2",
        password_hash=hash_password("admin2pass123"),
        role="admin",
        status=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# The protection itself
# ---------------------------------------------------------------------------


def test_another_admin_cannot_deactivate_the_system_admin(
    client, system_admin, second_admin
):
    headers = _auth_headers(client, "admin2", "admin2pass123")

    response = client.patch(
        f"/api/users/admins/{system_admin.id}/status",
        headers=headers,
        json={"status": False},
    )

    assert response.status_code == 403
    assert "system administrator" in response.json()["detail"].lower()


def test_the_system_admin_cannot_deactivate_itself(client, system_admin, second_admin):
    """Self-deactivation is what would otherwise lock everyone out."""
    headers = _auth_headers(client, "sysadmin", "sysadminpass123")

    response = client.patch(
        f"/api/users/admins/{system_admin.id}/status",
        headers=headers,
        json={"status": False},
    )

    assert response.status_code == 403


def test_protection_holds_even_when_other_admins_are_available(
    client, system_admin, second_admin, db_session
):
    """The guard must not depend on how many other admins happen to be
    active -- that is the separate last-admin rule, which is escapable by
    creating more accounts."""
    third = User(
        username="admin3",
        password_hash=hash_password("admin3pass123"),
        role="admin",
        status=True,
    )
    db_session.add(third)
    db_session.commit()

    headers = _auth_headers(client, "admin3", "admin3pass123")
    response = client.patch(
        f"/api/users/admins/{system_admin.id}/status",
        headers=headers,
        json={"status": False},
    )

    assert response.status_code == 403


def test_the_system_admin_stays_active_after_a_refused_attempt(
    client, system_admin, second_admin, db_session
):
    headers = _auth_headers(client, "admin2", "admin2pass123")
    client.patch(
        f"/api/users/admins/{system_admin.id}/status",
        headers=headers,
        json={"status": False},
    )

    db_session.expire_all()
    assert db_session.get(User, system_admin.id).status is True


def test_a_student_cannot_touch_the_system_admin(
    client, system_admin, student_user, student_profile
):
    headers = _auth_headers(client, "student1", "studentpass123")
    response = client.patch(
        f"/api/users/admins/{system_admin.id}/status",
        headers=headers,
        json={"status": False},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Everything else must still work
# ---------------------------------------------------------------------------


def test_ordinary_admins_can_still_be_deactivated(client, system_admin, second_admin):
    headers = _auth_headers(client, "sysadmin", "sysadminpass123")

    response = client.patch(
        f"/api/users/admins/{second_admin.id}/status",
        headers=headers,
        json={"status": False},
    )

    assert response.status_code == 200
    assert response.json()["status"] is False


def test_the_system_admin_can_be_reactivated(client, system_admin, second_admin):
    """Activation is never blocked -- only deactivation is."""
    headers = _auth_headers(client, "sysadmin", "sysadminpass123")
    response = client.patch(
        f"/api/users/admins/{system_admin.id}/status",
        headers=headers,
        json={"status": True},
    )
    assert response.status_code == 200


def test_the_flag_is_visible_so_the_ui_can_badge_and_lock_the_row(
    client, system_admin, second_admin
):
    headers = _auth_headers(client, "admin2", "admin2pass123")
    items = client.get("/api/users/admins", headers=headers).json()["items"]

    by_name = {item["username"]: item for item in items}
    assert by_name["sysadmin"]["is_system_admin"] is True
    assert by_name["admin2"]["is_system_admin"] is False


def test_a_normal_admin_created_via_the_api_is_never_a_system_admin(
    client, admin_user, db_session
):
    """The flag must not be settable over HTTP at all -- an extra field in
    the request body must be ignored, not honoured."""
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/users/admins",
        headers=headers,
        json={
            "username": "sneaky",
            "password": "sneakypass123",
            "is_system_admin": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["is_system_admin"] is False
    created = db_session.query(User).filter(User.username == "sneaky").first()
    assert created.is_system_admin is False


# ---------------------------------------------------------------------------
# The CLI that designates it
# ---------------------------------------------------------------------------


def test_cli_creates_a_designated_account(db_session):
    user = create(db_session, "root_admin", "rootpass123", "Root Administrator")

    assert user.is_system_admin is True
    assert user.role == "admin"
    assert user.status is True
    assert existing_system_admin(db_session).username == "root_admin"


def test_cli_promotes_an_existing_admin(db_session, second_admin):
    user = promote(db_session, "admin2")

    assert user.is_system_admin is True
    assert existing_system_admin(db_session).id == second_admin.id


def test_cli_promotion_reactivates_a_disabled_account(db_session, second_admin):
    """Designating a deactivated account as the one that can never be
    deactivated would leave a protected account nobody can log into."""
    second_admin.status = False
    db_session.commit()

    user = promote(db_session, "admin2")

    assert user.status is True


def test_cli_refuses_to_promote_a_student(db_session, student_user, student_profile):
    with pytest.raises(SystemAdminError, match="administrator"):
        promote(db_session, "student1")


def test_cli_refuses_an_unknown_account(db_session):
    with pytest.raises(SystemAdminError, match="No account"):
        promote(db_session, "nobody")


def test_cli_refuses_to_reuse_an_existing_username(db_session, second_admin):
    with pytest.raises(SystemAdminError, match="already exists"):
        create(db_session, "admin2", "somepass123", None)


def test_no_system_admin_exists_by_default(db_session, admin_user):
    assert existing_system_admin(db_session) is None
