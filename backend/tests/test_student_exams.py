from datetime import datetime, timedelta

from app.db.models import ExamSession, Student, User
from app.core.security import hash_password


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_second_student(db_session):
    user = User(
        username="student2",
        password_hash=hash_password("studentpass456"),
        role="student",
        status=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    student = Student(
        user_id=user.id,
        student_id="STU-2002",
        full_name="Second Student",
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return user, student


def _create_active_exam(client, admin_headers, duration_minutes=30, **overrides):
    payload = {
        "title": "Sample Exam",
        "description": "A sample exam",
        "duration_minutes": duration_minutes,
    }
    payload.update(overrides)
    exam = client.post("/api/exams", json=payload, headers=admin_headers).json()
    client.patch(
        f"/api/exams/{exam['id']}/status", json={"status": "active"}, headers=admin_headers
    )
    return exam


def _add_question(client, admin_headers, exam_id, correct_answer="B", **overrides):
    payload = {
        "question_text": "What is 2 + 2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_answer": correct_answer,
    }
    payload.update(overrides)
    return client.post(
        f"/api/exams/{exam_id}/questions", json=payload, headers=admin_headers
    ).json()


# ---------------------------------------------------------------------------


def test_student_sees_active_exam(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    response = client.get("/api/student/exams", headers=student_headers)
    assert response.status_code == 200
    exam_ids = [e["id"] for e in response.json()]
    assert exam["id"] in exam_ids


def test_student_cannot_see_correct_answers(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    _add_question(client, admin_headers, exam["id"])

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()
    response = client.get(
        f"/api/student/sessions/{session['id']}/questions", headers=student_headers
    )
    assert response.status_code == 200
    for question in response.json():
        assert "correct_answer" not in question


def test_student_starts_exam(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    response = client.post(f"/api/student/exams/{exam['id']}/start", headers=student_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["exam_id"] == exam["id"]
    assert body["status"] == "in_progress"


def test_student_gets_own_session(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()
    response = client.get(f"/api/student/sessions/{session['id']}", headers=student_headers)
    assert response.status_code == 200
    assert response.json()["id"] == session["id"]


def test_student_cannot_access_another_students_session(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()

    _make_second_student(db_session)
    other_headers = _auth_headers(client, "student2", "studentpass456")
    response = client.get(f"/api/student/sessions/{session['id']}", headers=other_headers)
    assert response.status_code == 404


def test_student_saves_answer(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    question = _add_question(client, admin_headers, exam["id"])

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()
    response = client.put(
        f"/api/student/sessions/{session['id']}/answers/{question['id']}",
        json={"selected_answer": "B"},
        headers=student_headers,
    )
    assert response.status_code == 200
    assert response.json()["selected_answer"] == "B"


def test_student_updates_answer(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    question = _add_question(client, admin_headers, exam["id"])

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()
    client.put(
        f"/api/student/sessions/{session['id']}/answers/{question['id']}",
        json={"selected_answer": "A"},
        headers=student_headers,
    )
    response = client.put(
        f"/api/student/sessions/{session['id']}/answers/{question['id']}",
        json={"selected_answer": "C"},
        headers=student_headers,
    )
    assert response.status_code == 200
    assert response.json()["selected_answer"] == "C"


def test_student_cannot_modify_another_students_answer(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    question = _add_question(client, admin_headers, exam["id"])

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()

    _make_second_student(db_session)
    other_headers = _auth_headers(client, "student2", "studentpass456")
    response = client.put(
        f"/api/student/sessions/{session['id']}/answers/{question['id']}",
        json={"selected_answer": "A"},
        headers=other_headers,
    )
    assert response.status_code == 404


def test_invalid_exam_rejected(client, admin_user, student_user, student_profile):
    student_headers = _auth_headers(client, "student1", "studentpass123")
    response = client.post("/api/student/exams/999999/start", headers=student_headers)
    assert response.status_code == 404


def test_inactive_exam_rejected(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = client.post(
        "/api/exams",
        json={"title": "Draft Exam", "duration_minutes": 30},
        headers=admin_headers,
    ).json()

    student_headers = _auth_headers(client, "student1", "studentpass123")
    response = client.post(f"/api/student/exams/{exam['id']}/start", headers=student_headers)
    assert response.status_code == 404


def test_duplicate_active_session_resumes(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    first = client.post(f"/api/student/exams/{exam['id']}/start", headers=student_headers).json()
    second = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    )
    assert second.status_code == 200
    assert second.json()["id"] == first["id"]


def test_expired_session_handled(client, admin_user, student_user, student_profile, db_session):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers, duration_minutes=5)
    question = _add_question(client, admin_headers, exam["id"])

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()

    row = db_session.get(ExamSession, session["id"])
    row.started_at = datetime.utcnow() - timedelta(minutes=10)
    db_session.commit()

    response = client.get(f"/api/student/sessions/{session['id']}", headers=student_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "expired"

    answer_response = client.put(
        f"/api/student/sessions/{session['id']}/answers/{question['id']}",
        json={"selected_answer": "A"},
        headers=student_headers,
    )
    assert answer_response.status_code == 409

    submit_response = client.post(
        f"/api/student/sessions/{session['id']}/submit", headers=student_headers
    )
    assert submit_response.status_code == 409


def test_student_submits_exam_and_result_calculated(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    q1 = _add_question(client, admin_headers, exam["id"], correct_answer="B")
    q2 = _add_question(client, admin_headers, exam["id"], correct_answer="A")

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()

    client.put(
        f"/api/student/sessions/{session['id']}/answers/{q1['id']}",
        json={"selected_answer": "B"},
        headers=student_headers,
    )
    client.put(
        f"/api/student/sessions/{session['id']}/answers/{q2['id']}",
        json={"selected_answer": "D"},
        headers=student_headers,
    )

    response = client.post(
        f"/api/student/sessions/{session['id']}/submit", headers=student_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "submitted"
    assert body["total_questions"] == 2
    assert body["answered_questions"] == 2
    assert body["score"] == 50


def test_submitted_exam_cannot_be_modified(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    question = _add_question(client, admin_headers, exam["id"])

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()
    client.post(f"/api/student/sessions/{session['id']}/submit", headers=student_headers)

    response = client.put(
        f"/api/student/sessions/{session['id']}/answers/{question['id']}",
        json={"selected_answer": "A"},
        headers=student_headers,
    )
    assert response.status_code == 409


def test_duplicate_submission_rejected(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()
    client.post(f"/api/student/sessions/{session['id']}/submit", headers=student_headers)

    response = client.post(
        f"/api/student/sessions/{session['id']}/submit", headers=student_headers
    )
    assert response.status_code == 409


def test_admin_access_remains_functional(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/exams",
        json={"title": "Admin Check Exam", "duration_minutes": 20},
        headers=admin_headers,
    )
    assert response.status_code == 201


def test_unauthenticated_student_endpoints_rejected(client):
    assert client.get("/api/student/exams").status_code == 401
    assert client.post("/api/student/exams/1/start").status_code == 401
