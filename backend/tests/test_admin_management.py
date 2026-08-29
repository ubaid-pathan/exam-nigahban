from app.core.security import hash_password
from app.db.models import Student, User


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_admin(db_session, *, username, status=True):
    user = User(
        username=username,
        password_hash=hash_password("adminpass123"),
        role="admin",
        status=status,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_student_row(db_session, *, username="astudent", student_id="STU-1001"):
    user = User(
        username=username,
        password_hash=hash_password("studentpass123"),
        role="student",
        status=True,
    )
    db_session.add(user)
    db_session.flush()
    student = Student(
        user_id=user.id,
        student_id=student_id,
        full_name="A Student",
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# GET /api/users/admins -- list
# ---------------------------------------------------------------------------


def test_admin_list_contains_only_the_calling_admin_by_default(client, admin_user):
    # A caller must itself be an authenticated admin, so a literal empty
    # list is unreachable -- this is the baseline/minimal-state equivalent.
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.get("/api/users/admins", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["username"] == "admin1"


def test_admin_list_returns_all_fields(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.get("/api/users/admins", headers=headers)
    item = response.json()["items"][0]
    assert item["id"] == admin_user.id
    assert item["username"] == "admin1"
    assert item["role"] == "admin"
    assert item["status"] is True
    assert "created_at" in item
    assert "password_hash" not in item


def test_admin_list_excludes_students(client, admin_user, db_session):
    _create_student_row(db_session)
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.get("/api/users/admins", headers=headers)
    body = response.json()
    assert body["total"] == 1
    assert all(item["role"] == "admin" for item in body["items"])


def test_admin_list_search_matches_username(client, admin_user, db_session):
    _create_admin(db_session, username="secondadmin")
    headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.get("/api/users/admins?search=second", headers=headers)
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["username"] == "secondadmin"


def test_admin_list_search_no_match_returns_empty(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.get("/api/users/admins?search=nonexistent", headers=headers)
    assert response.json()["total"] == 0


def test_admin_list_pagination_works(client, admin_user, db_session):
    for i in range(3):
        _create_admin(db_session, username=f"admin_extra_{i}")
    headers = _auth_headers(client, "admin1", "adminpass123")

    page_1 = client.get("/api/users/admins?page=1&page_size=2", headers=headers).json()
    assert len(page_1["items"]) == 2
    assert page_1["total"] == 4
    assert page_1["total_pages"] == 2

    page_2 = client.get("/api/users/admins?page=2&page_size=2", headers=headers).json()
    assert len(page_2["items"]) == 2

    ids_page_1 = {item["id"] for item in page_1["items"]}
    ids_page_2 = {item["id"] for item in page_2["items"]}
    assert ids_page_1.isdisjoint(ids_page_2)


def test_admin_list_invalid_page_returns_422(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    assert client.get("/api/users/admins?page=0", headers=headers).status_code == 422


def test_admin_list_invalid_page_size_returns_422(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    assert client.get("/api/users/admins?page_size=101", headers=headers).status_code == 422


def test_admin_list_unauthenticated_rejected(client):
    assert client.get("/api/users/admins").status_code == 401


def test_admin_list_student_role_rejected(client, admin_user, student_user):
    headers = _auth_headers(client, "student1", "studentpass123")
    assert client.get("/api/users/admins", headers=headers).status_code == 403


# ---------------------------------------------------------------------------
# GET /api/users/admins/{user_id} -- detail
# ---------------------------------------------------------------------------


def test_get_admin_detail_returns_fields(client, admin_user, db_session):
    second = _create_admin(db_session, username="secondadmin")
    headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.get(f"/api/users/admins/{second.id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == second.id
    assert body["username"] == "secondadmin"


def test_get_admin_detail_not_found_returns_404(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    assert client.get("/api/users/admins/999999", headers=headers).status_code == 404


def test_get_admin_detail_student_target_returns_404(client, admin_user, db_session):
    student_user_row = _create_student_row(db_session)
    headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.get(f"/api/users/admins/{student_user_row.id}", headers=headers)
    assert response.status_code == 404


def test_get_admin_detail_unauthenticated_rejected(client, admin_user):
    assert client.get(f"/api/users/admins/{admin_user.id}").status_code == 401


def test_get_admin_detail_student_role_rejected(client, admin_user, student_user):
    headers = _auth_headers(client, "student1", "studentpass123")
    response = client.get(f"/api/users/admins/{admin_user.id}", headers=headers)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/users/admins/{user_id}/status
# ---------------------------------------------------------------------------


def test_deactivate_other_admin_succeeds(client, admin_user, db_session):
    second = _create_admin(db_session, username="secondadmin")
    headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.patch(
        f"/api/users/admins/{second.id}/status", json={"status": False}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"] is False


def test_activate_inactive_admin_succeeds(client, admin_user, db_session):
    second = _create_admin(db_session, username="secondadmin", status=False)
    headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.patch(
        f"/api/users/admins/{second.id}/status", json={"status": True}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"] is True


def test_deactivated_admin_login_blocked(client, admin_user, db_session):
    second = _create_admin(db_session, username="secondadmin")
    headers = _auth_headers(client, "admin1", "adminpass123")

    client.patch(f"/api/users/admins/{second.id}/status", json={"status": False}, headers=headers)

    login_response = client.post(
        "/api/auth/login", json={"username": "secondadmin", "password": "adminpass123"}
    )
    assert login_response.status_code == 401


def test_reactivated_admin_login_restored(client, admin_user, db_session):
    second = _create_admin(db_session, username="secondadmin", status=False)
    headers = _auth_headers(client, "admin1", "adminpass123")

    client.patch(f"/api/users/admins/{second.id}/status", json={"status": True}, headers=headers)

    login_response = client.post(
        "/api/auth/login", json={"username": "secondadmin", "password": "adminpass123"}
    )
    assert login_response.status_code == 200


def test_self_deactivation_rejected_with_another_active_admin_present(client, admin_user, db_session):
    # Two active admins exist, so this is NOT the last-active-admin case --
    # it must be rejected purely because it's a self-deactivation attempt.
    _create_admin(db_session, username="secondadmin")
    headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.patch(
        f"/api/users/admins/{admin_user.id}/status", json={"status": False}, headers=headers
    )
    assert response.status_code == 409
    assert "own account" in response.json()["detail"].lower()

    # Status must be unchanged.
    detail = client.get(f"/api/users/admins/{admin_user.id}", headers=headers).json()
    assert detail["status"] is True


def test_last_active_admin_deactivation_rejected(client, admin_user):
    # admin_user is the sole active admin, deactivating themself would leave
    # zero active admins -- must be rejected as the last-admin case.
    headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.patch(
        f"/api/users/admins/{admin_user.id}/status", json={"status": False}, headers=headers
    )
    assert response.status_code == 409
    assert "last remaining" in response.json()["detail"].lower()

    detail = client.get(f"/api/users/admins/{admin_user.id}", headers=headers).json()
    assert detail["status"] is True


def test_deactivating_one_of_two_active_admins_is_allowed(client, admin_user, db_session):
    # Sanity check that the last-admin rule does not over-block: deactivating
    # one of two active admins (not self) always succeeds, since the caller
    # remains active regardless of which other admin is targeted.
    second = _create_admin(db_session, username="secondadmin")
    headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.patch(
        f"/api/users/admins/{second.id}/status", json={"status": False}, headers=headers
    )
    assert response.status_code == 200


def test_status_update_not_found_returns_404(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.patch(
        "/api/users/admins/999999/status", json={"status": False}, headers=headers
    )
    assert response.status_code == 404


def test_status_update_unauthenticated_rejected(client, admin_user, db_session):
    second = _create_admin(db_session, username="secondadmin")
    response = client.patch(f"/api/users/admins/{second.id}/status", json={"status": False})
    assert response.status_code == 401


def test_status_update_student_role_rejected(client, admin_user, student_user, db_session):
    second = _create_admin(db_session, username="secondadmin")
    headers = _auth_headers(client, "student1", "studentpass123")
    response = client.patch(
        f"/api/users/admins/{second.id}/status", json={"status": False}, headers=headers
    )
    assert response.status_code == 403


def test_existing_admin_creation_endpoint_still_functional(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/users/admins",
        json={"username": "newadmin", "password": "newadminpass123"},
        headers=headers,
    )
    assert response.status_code == 201
