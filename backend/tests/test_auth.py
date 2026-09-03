def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_login_success(client, admin_user):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin1", "password": "adminpass123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_student_login_success(client, student_user):
    response = client.post(
        "/api/auth/login",
        json={"username": "student1", "password": "studentpass123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_invalid_password(client, admin_user):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin1", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_login_unknown_username(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "doesnotexist", "password": "whatever123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_login_inactive_account_rejected(client, inactive_user):
    response = client.post(
        "/api/auth/login",
        json={"username": "inactive1", "password": "inactivepass123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Account is inactive"


def test_me_without_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_valid_token(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "admin1"
    assert body["role"] == "admin"


def test_me_with_invalid_token(client):
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not.a.validtoken"},
    )
    assert response.status_code == 401


def test_logout_with_valid_token(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 200
    assert "detail" in response.json()


def test_logout_without_token(client):
    response = client.post("/api/auth/logout")
    assert response.status_code == 401


def test_admin_creates_student(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/users/students",
        json={
            "username": "newstudent",
            "password": "studentpass123",
            "student_id": "STU-9001",
            "full_name": "New Student",
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "newstudent"
    assert body["role"] == "student"


def test_admin_creates_admin(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/users/admins",
        json={"username": "newadmin", "password": "adminpass456"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "newadmin"
    assert body["role"] == "admin"


def test_admin_creates_student_with_email(client, admin_user):
    # email/full_name-for-admins were added for the Users consolidation
    # feature -- both are optional at the schema level (see
    # test_admin_creates_student/test_admin_creates_admin above, which omit
    # them entirely and must keep working), but must be accepted and
    # returned correctly when the caller does provide them.
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/users/students",
        json={
            "username": "emailstudent",
            "password": "studentpass123",
            "student_id": "STU-9010",
            "full_name": "Email Student",
            "email": "emailstudent@example.com",
        },
        headers=headers,
    )
    assert response.status_code == 201

    listing = client.get("/api/users/students", headers=headers).json()
    item = next(i for i in listing["items"] if i["username"] == "emailstudent")
    assert item["email"] == "emailstudent@example.com"


def test_admin_creates_student_with_invalid_email_rejected(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/users/students",
        json={
            "username": "bademailstudent",
            "password": "studentpass123",
            "student_id": "STU-9011",
            "full_name": "Bad Email Student",
            "email": "not-an-email",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_admin_creates_admin_with_full_name_and_email(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/users/admins",
        json={
            "username": "fulladmin",
            "password": "adminpass456",
            "full_name": "Full Admin",
            "email": "fulladmin@example.com",
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["full_name"] == "Full Admin"
    assert body["email"] == "fulladmin@example.com"


def test_admin_creates_admin_with_invalid_email_rejected(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/users/admins",
        json={"username": "bademailadmin", "password": "adminpass456", "email": "nope"},
        headers=headers,
    )
    assert response.status_code == 422


def test_duplicate_username_rejected(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/users/admins",
        json={"username": "admin1", "password": "somepassword"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already exists"


def test_duplicate_student_id_rejected(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    first = client.post(
        "/api/users/students",
        json={
            "username": "student_a",
            "password": "studentpass123",
            "student_id": "STU-9002",
            "full_name": "Student A",
        },
        headers=headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/api/users/students",
        json={
            "username": "student_b",
            "password": "studentpass123",
            "student_id": "STU-9002",
            "full_name": "Student B",
        },
        headers=headers,
    )
    assert second.status_code == 400
    assert second.json()["detail"] == "Student ID already exists"


def test_student_forbidden_from_admin_routes(client, student_user):
    headers = _auth_headers(client, "student1", "studentpass123")
    response = client.post(
        "/api/users/admins",
        json={"username": "shouldnotbecreated", "password": "somepassword"},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"

def test_admin_forbidden_from_student_routes(client, admin_user):
    headers = _auth_headers(
        client,
        "admin1",
        "adminpass123",
    )

    response = client.get(
        "/api/student/exams",
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Student access required"