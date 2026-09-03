from app.core.security import hash_password
from app.db.models import Student, User


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_student(db_session, *, username, student_id, full_name, department=None,
                     class_name=None, account_status=True, is_active=True):
    user = User(
        username=username,
        password_hash=hash_password("studentpass123"),
        role="student",
        status=account_status,
    )
    db_session.add(user)
    db_session.flush()

    student = Student(
        user_id=user.id,
        student_id=student_id,
        full_name=full_name,
        department=department,
        class_name=class_name,
        is_active=is_active,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


# ---------------------------------------------------------------------------
# GET /api/users/students -- list
# ---------------------------------------------------------------------------


def test_empty_student_list_returns_valid_empty_response(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.get("/api/users/students", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["total_pages"] == 0
    assert body["page"] == 1
    assert body["page_size"] == 20


def test_populated_student_list_returns_all_fields(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    _create_student(
        db_session,
        username="alice",
        student_id="STU-1001",
        full_name="Alice Example",
        department="Computer Science",
        class_name="CS-101",
    )

    response = client.get("/api/users/students", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["username"] == "alice"
    assert item["student_id"] == "STU-1001"
    assert item["full_name"] == "Alice Example"
    assert item["department"] == "Computer Science"
    assert item["class_name"] == "CS-101"
    assert item["is_active"] is True
    assert item["account_status"] is True
    assert "id" in item and "user_id" in item and "created_at" in item
    assert "password_hash" not in item


def test_student_list_search_matches_full_name(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    _create_student(db_session, username="alice", student_id="STU-1001", full_name="Alice Example")
    _create_student(db_session, username="bob", student_id="STU-1002", full_name="Bob Sample")

    response = client.get("/api/users/students?search=Alice", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["full_name"] == "Alice Example"


def test_student_list_search_matches_student_id(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    _create_student(db_session, username="alice", student_id="STU-1001", full_name="Alice Example")
    _create_student(db_session, username="bob", student_id="STU-1002", full_name="Bob Sample")

    response = client.get("/api/users/students?search=STU-1002", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["student_id"] == "STU-1002"


def test_student_list_search_matches_username(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    _create_student(db_session, username="alice", student_id="STU-1001", full_name="Alice Example")
    _create_student(db_session, username="bob", student_id="STU-1002", full_name="Bob Sample")

    response = client.get("/api/users/students?search=bob", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["username"] == "bob"


def test_student_list_search_no_match_returns_empty(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    _create_student(db_session, username="alice", student_id="STU-1001", full_name="Alice Example")

    response = client.get("/api/users/students?search=nonexistent", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_student_list_pagination_works(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    for i in range(3):
        _create_student(
            db_session,
            username=f"student{i}",
            student_id=f"STU-100{i}",
            full_name=f"Student {i}",
        )

    page_1 = client.get("/api/users/students?page=1&page_size=2", headers=headers).json()
    assert len(page_1["items"]) == 2
    assert page_1["total"] == 3
    assert page_1["total_pages"] == 2
    assert page_1["page"] == 1
    assert page_1["page_size"] == 2

    page_2 = client.get("/api/users/students?page=2&page_size=2", headers=headers).json()
    assert len(page_2["items"]) == 1
    assert page_2["page"] == 2

    ids_page_1 = {item["id"] for item in page_1["items"]}
    ids_page_2 = {item["id"] for item in page_2["items"]}
    assert ids_page_1.isdisjoint(ids_page_2)


def test_student_list_invalid_page_returns_422(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    assert client.get("/api/users/students?page=0", headers=headers).status_code == 422
    assert client.get("/api/users/students?page=-1", headers=headers).status_code == 422


def test_student_list_invalid_page_size_returns_422(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    assert client.get("/api/users/students?page_size=0", headers=headers).status_code == 422
    assert client.get("/api/users/students?page_size=101", headers=headers).status_code == 422


def test_student_list_unauthenticated_rejected(client):
    response = client.get("/api/users/students")
    assert response.status_code == 401


def test_student_list_student_role_rejected(client, student_user):
    headers = _auth_headers(client, "student1", "studentpass123")
    response = client.get("/api/users/students", headers=headers)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/users/students/{student_id} -- detail
# ---------------------------------------------------------------------------


def test_get_student_detail_returns_all_fields(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    student = _create_student(
        db_session,
        username="alice",
        student_id="STU-1001",
        full_name="Alice Example",
        department="Computer Science",
        class_name="CS-101",
    )

    response = client.get(f"/api/users/students/{student.id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == student.id
    assert body["username"] == "alice"
    assert body["student_id"] == "STU-1001"
    assert body["full_name"] == "Alice Example"
    assert body["is_active"] is True
    assert body["account_status"] is True


def test_get_student_detail_not_found_returns_404(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.get("/api/users/students/999999", headers=headers)
    assert response.status_code == 404


def test_get_student_detail_unauthenticated_rejected(client, admin_user, db_session):
    student = _create_student(db_session, username="alice", student_id="STU-1001", full_name="Alice Example")
    response = client.get(f"/api/users/students/{student.id}")
    assert response.status_code == 401


def test_get_student_detail_student_role_rejected(client, admin_user, student_user, db_session):
    student = _create_student(db_session, username="alice", student_id="STU-1001", full_name="Alice Example")
    headers = _auth_headers(client, "student1", "studentpass123")
    response = client.get(f"/api/users/students/{student.id}", headers=headers)
    assert response.status_code == 403


def test_get_student_detail_reflects_inactive_account(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    student = _create_student(
        db_session,
        username="dormant",
        student_id="STU-2001",
        full_name="Dormant Student",
        account_status=False,
        is_active=False,
    )

    response = client.get(f"/api/users/students/{student.id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["account_status"] is False
    assert body["is_active"] is False


def test_existing_student_creation_endpoint_still_functional(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/users/students",
        json={
            "username": "newstudent",
            "password": "newstudentpass123",
            "student_id": "STU-3001",
            "full_name": "New Student",
        },
        headers=headers,
    )
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# PUT /api/users/students/{student_id} -- update
# ---------------------------------------------------------------------------


def test_update_student_persists_profile_fields(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    student = _create_student(
        db_session,
        username="alice",
        student_id="STU-1001",
        full_name="Alice Example",
        department="Computer Science",
        class_name="CS-101",
    )

    response = client.put(
        f"/api/users/students/{student.id}",
        json={
            "full_name": "Alice Updated",
            "department": "Software Engineering",
            "class_name": "SE-201",
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Alice Updated"
    assert body["department"] == "Software Engineering"
    assert body["class_name"] == "SE-201"

    # Persisted, not just echoed back.
    refetched = client.get(f"/api/users/students/{student.id}", headers=headers).json()
    assert refetched["full_name"] == "Alice Updated"
    assert refetched["department"] == "Software Engineering"
    assert refetched["class_name"] == "SE-201"


def test_update_student_allows_clearing_optional_fields(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    student = _create_student(
        db_session,
        username="alice",
        student_id="STU-1001",
        full_name="Alice Example",
        department="Computer Science",
        class_name="CS-101",
    )

    response = client.put(
        f"/api/users/students/{student.id}",
        json={"full_name": "Alice Example", "department": None, "class_name": None},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["department"] is None
    assert body["class_name"] is None


def test_update_student_cannot_change_username_or_student_id(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    student = _create_student(
        db_session, username="alice", student_id="STU-1001", full_name="Alice Example"
    )

    response = client.put(
        f"/api/users/students/{student.id}",
        json={
            "full_name": "Alice Example",
            "username": "hacker",
            "student_id": "STU-9999",
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["student_id"] == "STU-1001"


def test_update_student_rejects_empty_full_name(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    student = _create_student(
        db_session, username="alice", student_id="STU-1001", full_name="Alice Example"
    )

    response = client.put(
        f"/api/users/students/{student.id}",
        json={"full_name": "", "department": None, "class_name": None},
        headers=headers,
    )
    assert response.status_code == 422


def test_update_student_not_found_returns_404(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.put(
        "/api/users/students/999999",
        json={"full_name": "Nobody", "department": None, "class_name": None},
        headers=headers,
    )
    assert response.status_code == 404


def test_update_student_unauthenticated_rejected(client, admin_user, db_session):
    student = _create_student(
        db_session, username="alice", student_id="STU-1001", full_name="Alice Example"
    )
    response = client.put(
        f"/api/users/students/{student.id}",
        json={"full_name": "Alice Example", "department": None, "class_name": None},
    )
    assert response.status_code == 401


def test_update_student_student_role_rejected(client, admin_user, student_user, db_session):
    student = _create_student(
        db_session, username="alice", student_id="STU-1001", full_name="Alice Example"
    )
    headers = _auth_headers(client, "student1", "studentpass123")
    response = client.put(
        f"/api/users/students/{student.id}",
        json={"full_name": "Alice Example", "department": None, "class_name": None},
        headers=headers,
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/users/students/{student_id}/status -- activate/deactivate
# ---------------------------------------------------------------------------


def test_deactivate_student_sets_both_status_fields_false(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    student = _create_student(
        db_session, username="alice", student_id="STU-1001", full_name="Alice Example"
    )

    response = client.patch(
        f"/api/users/students/{student.id}/status",
        json={"is_active": False},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is False
    assert body["account_status"] is False


def test_activate_student_sets_both_status_fields_true(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    student = _create_student(
        db_session,
        username="alice",
        student_id="STU-1001",
        full_name="Alice Example",
        account_status=False,
        is_active=False,
    )

    response = client.patch(
        f"/api/users/students/{student.id}/status",
        json={"is_active": True},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is True
    assert body["account_status"] is True


def test_deactivate_student_blocks_subsequent_login(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    student = _create_student(
        db_session, username="alice", student_id="STU-1001", full_name="Alice Example"
    )

    client.patch(
        f"/api/users/students/{student.id}/status",
        json={"is_active": False},
        headers=headers,
    )

    login_response = client.post(
        "/api/auth/login", json={"username": "alice", "password": "studentpass123"}
    )
    assert login_response.status_code == 401


def test_reactivate_student_restores_login(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    student = _create_student(
        db_session,
        username="alice",
        student_id="STU-1001",
        full_name="Alice Example",
        account_status=False,
        is_active=False,
    )

    client.patch(
        f"/api/users/students/{student.id}/status",
        json={"is_active": True},
        headers=headers,
    )

    login_response = client.post(
        "/api/auth/login", json={"username": "alice", "password": "studentpass123"}
    )
    assert login_response.status_code == 200


def test_status_update_persists_via_get(client, admin_user, db_session):
    headers = _auth_headers(client, "admin1", "adminpass123")
    student = _create_student(
        db_session, username="alice", student_id="STU-1001", full_name="Alice Example"
    )

    client.patch(
        f"/api/users/students/{student.id}/status",
        json={"is_active": False},
        headers=headers,
    )

    refetched = client.get(f"/api/users/students/{student.id}", headers=headers).json()
    assert refetched["is_active"] is False
    assert refetched["account_status"] is False


def test_status_update_does_not_touch_exam_session(client, admin_user, db_session):
    """Deactivation must never mutate ExamSession -- Stage 2 is explicitly
    scoped to blocking future login/access only (see users.py::update_student_status)."""
    from datetime import datetime

    from app.db.models import Exam, ExamSession

    headers = _auth_headers(client, "admin1", "adminpass123")
    student = _create_student(
        db_session, username="alice", student_id="STU-1001", full_name="Alice Example"
    )

    exam = Exam(title="Demo Exam", description=None, duration_minutes=60, status="active")
    db_session.add(exam)
    db_session.flush()

    session_row = ExamSession(
        student_id=student.id,
        exam_id=exam.id,
        started_at=datetime.utcnow(),
        status="in_progress",
    )
    db_session.add(session_row)
    db_session.commit()
    db_session.refresh(session_row)

    client.patch(
        f"/api/users/students/{student.id}/status",
        json={"is_active": False},
        headers=headers,
    )

    db_session.refresh(session_row)
    assert session_row.status == "in_progress"
    assert session_row.ended_at is None


def test_status_update_not_found_returns_404(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.patch(
        "/api/users/students/999999/status",
        json={"is_active": False},
        headers=headers,
    )
    assert response.status_code == 404


def test_status_update_unauthenticated_rejected(client, admin_user, db_session):
    student = _create_student(
        db_session, username="alice", student_id="STU-1001", full_name="Alice Example"
    )
    response = client.patch(
        f"/api/users/students/{student.id}/status", json={"is_active": False}
    )
    assert response.status_code == 401


def test_status_update_student_role_rejected(client, admin_user, student_user, db_session):
    student = _create_student(
        db_session, username="alice", student_id="STU-1001", full_name="Alice Example"
    )
    headers = _auth_headers(client, "student1", "studentpass123")
    response = client.patch(
        f"/api/users/students/{student.id}/status",
        json={"is_active": False},
        headers=headers,
    )
    assert response.status_code == 403
