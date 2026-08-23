def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_exam(client, headers, **overrides):
    payload = {
        "title": "Demo Exam",
        "description": "A demo exam",
        "duration_minutes": 60,
    }
    payload.update(overrides)
    return client.post("/api/exams", json=payload, headers=headers)


def _create_question(client, headers, exam_id, **overrides):
    payload = {
        "question_text": "What is 2 + 2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_answer": "B",
    }
    payload.update(overrides)
    return client.post(f"/api/exams/{exam_id}/questions", json=payload, headers=headers)


# ---------------------------------------------------------------------------
# EXAMS
# ---------------------------------------------------------------------------


def test_admin_creates_exam(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = _create_exam(client, headers)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Demo Exam"
    assert body["status"] == "draft"


def test_create_exam_unauthenticated_rejected(client):
    response = _create_exam(client, headers={})
    assert response.status_code == 401


def test_create_exam_student_rejected(client, student_user):
    headers = _auth_headers(client, "student1", "studentpass123")
    response = _create_exam(client, headers)
    assert response.status_code == 403


def test_list_exams(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    _create_exam(client, headers, title="Exam A")
    _create_exam(client, headers, title="Exam B")
    response = client.get("/api/exams", headers=headers)
    assert response.status_code == 200
    titles = [exam["title"] for exam in response.json()]
    assert "Exam A" in titles
    assert "Exam B" in titles


def test_get_exam(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, headers).json()["id"]
    response = client.get(f"/api/exams/{exam_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == exam_id


def test_update_exam(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, headers).json()["id"]
    response = client.put(
        f"/api/exams/{exam_id}",
        json={"title": "Updated Exam", "description": "Updated", "duration_minutes": 90},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated Exam"
    assert body["duration_minutes"] == 90


def test_activate_exam(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, headers).json()["id"]
    response = client.patch(
        f"/api/exams/{exam_id}/status", json={"status": "active"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_deactivate_exam(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, headers).json()["id"]
    client.patch(f"/api/exams/{exam_id}/status", json={"status": "active"}, headers=headers)
    response = client.patch(
        f"/api/exams/{exam_id}/status", json={"status": "inactive"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"


def test_get_invalid_exam_id(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.get("/api/exams/999999", headers=headers)
    assert response.status_code == 404


def test_create_exam_invalid_data(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = _create_exam(client, headers, duration_minutes=-10)
    assert response.status_code == 422


def test_delete_exam_without_questions(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, headers).json()["id"]
    response = client.delete(f"/api/exams/{exam_id}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/api/exams/{exam_id}", headers=headers).status_code == 404


def test_delete_exam_with_questions_conflict(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, headers).json()["id"]
    _create_question(client, headers, exam_id)
    response = client.delete(f"/api/exams/{exam_id}", headers=headers)
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# QUESTIONS
# ---------------------------------------------------------------------------


def test_admin_creates_question(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, headers).json()["id"]
    response = _create_question(client, headers, exam_id)
    assert response.status_code == 201
    body = response.json()
    assert body["exam_id"] == exam_id
    assert body["correct_answer"] == "B"


def test_create_question_unauthenticated_rejected(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, headers).json()["id"]
    response = _create_question(client, headers={}, exam_id=exam_id)
    assert response.status_code == 401


def test_create_question_student_rejected(client, admin_user, student_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, admin_headers).json()["id"]
    student_headers = _auth_headers(client, "student1", "studentpass123")
    response = _create_question(client, student_headers, exam_id)
    assert response.status_code == 403


def test_list_questions(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, headers).json()["id"]
    _create_question(client, headers, exam_id, question_text="Q1")
    _create_question(client, headers, exam_id, question_text="Q2")
    response = client.get(f"/api/exams/{exam_id}/questions", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_question(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, headers).json()["id"]
    question_id = _create_question(client, headers, exam_id).json()["id"]
    response = client.get(f"/api/questions/{question_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == question_id


def test_update_question(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, headers).json()["id"]
    question_id = _create_question(client, headers, exam_id).json()["id"]
    response = client.put(
        f"/api/questions/{question_id}",
        json={
            "question_text": "What is 3 + 3?",
            "option_a": "5",
            "option_b": "6",
            "option_c": "7",
            "option_d": "8",
            "correct_answer": "B",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["question_text"] == "What is 3 + 3?"


def test_delete_question(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    exam_id = _create_exam(client, headers).json()["id"]
    question_id = _create_question(client, headers, exam_id).json()["id"]
    response = client.delete(f"/api/questions/{question_id}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/api/questions/{question_id}", headers=headers).status_code == 404


def test_create_question_invalid_exam_id(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = _create_question(client, headers, exam_id=999999)
    assert response.status_code == 404


def test_get_invalid_question_id(client, admin_user):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.get("/api/questions/999999", headers=headers)
    assert response.status_code == 404
