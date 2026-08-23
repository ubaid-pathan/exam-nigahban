from datetime import datetime, timedelta

from app.db.models import ExamSession, MonitoringEvent, Student, User
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


def _create_active_exam(client, admin_headers, duration_minutes=30):
    payload = {
        "title": "Sample Exam",
        "description": "A sample exam",
        "duration_minutes": duration_minutes,
    }
    exam = client.post("/api/exams", json=payload, headers=admin_headers).json()
    client.patch(
        f"/api/exams/{exam['id']}/status", json={"status": "active"}, headers=admin_headers
    )
    return exam


def _valid_event_payload(session_id, **overrides):
    payload = {
        "session_id": session_id,
        "event_type": "HEAD_LEFT",
        "severity": "medium",
        "confidence": 0.87,
        "duration_seconds": 4.2,
        "occurrences": 3,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------


def test_student_records_monitoring_event_for_own_active_session(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()

    response = client.post(
        "/api/monitoring/events",
        json=_valid_event_payload(session["id"]),
        headers=student_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["session_id"] == session["id"]
    assert body["event_type"] == "HEAD_LEFT"
    assert body["severity"] == "medium"
    assert body["status"] == "PENDING_REVIEW"
    assert body["source"] == "browser_mediapipe"


def test_student_cannot_record_event_for_another_students_session(
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
    response = client.post(
        "/api/monitoring/events",
        json=_valid_event_payload(session["id"]),
        headers=other_headers,
    )
    assert response.status_code == 404

    # Confirm the event was never persisted under the other student's request.
    assert db_session.query(MonitoringEvent).count() == 0


def test_event_rejected_for_nonexistent_session(
    client, admin_user, student_user, student_profile
):
    student_headers = _auth_headers(client, "student1", "studentpass123")
    response = client.post(
        "/api/monitoring/events",
        json=_valid_event_payload(999999),
        headers=student_headers,
    )
    assert response.status_code == 404


def test_event_rejected_for_expired_session(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers, duration_minutes=5)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()

    row = db_session.get(ExamSession, session["id"])
    row.started_at = datetime.utcnow() - timedelta(minutes=10)
    db_session.commit()

    response = client.post(
        "/api/monitoring/events",
        json=_valid_event_payload(session["id"]),
        headers=student_headers,
    )
    assert response.status_code == 409


def test_event_rejected_for_submitted_session(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()
    client.post(f"/api/student/sessions/{session['id']}/submit", headers=student_headers)

    response = client.post(
        "/api/monitoring/events",
        json=_valid_event_payload(session["id"]),
        headers=student_headers,
    )
    assert response.status_code == 409


def test_event_rejected_with_invalid_event_type(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()

    response = client.post(
        "/api/monitoring/events",
        json=_valid_event_payload(session["id"], event_type="CHEATING_CONFIRMED"),
        headers=student_headers,
    )
    assert response.status_code == 422


def test_event_rejected_with_out_of_range_confidence(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()

    response = client.post(
        "/api/monitoring/events",
        json=_valid_event_payload(session["id"], confidence=1.5),
        headers=student_headers,
    )
    assert response.status_code == 422


def test_admin_cannot_record_monitoring_events(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/monitoring/events",
        json=_valid_event_payload(1),
        headers=admin_headers,
    )
    assert response.status_code == 403


def test_unauthenticated_monitoring_request_rejected(client):
    response = client.post("/api/monitoring/events", json=_valid_event_payload(1))
    assert response.status_code == 401
