from datetime import datetime, timedelta

from app.db.models import ExamSession, MonitoringEvent, MonitoringRule, Student, User
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


# ---------------------------------------------------------------------------
# MOBILE_PHONE (Milestone 6 Phase 2 Step 5 -- YOLOX Worker pipeline)
# ---------------------------------------------------------------------------


def _fake_jpeg_base64() -> str:
    import base64

    return base64.b64encode(b"\xff\xd8\xff" + b"\x00" * 64).decode("ascii")


def test_mobile_phone_event_accepted_with_high_severity(
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
        json=_valid_event_payload(
            session["id"],
            event_type="MOBILE_PHONE",
            severity="high",
            confidence=0.9213,
            duration_seconds=1.1,
            occurrences=1,
        ),
        headers=student_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["event_type"] == "MOBILE_PHONE"
    assert body["severity"] == "high"


def test_mobile_phone_event_with_evidence_stores_evidence(
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
        json=_valid_event_payload(
            session["id"],
            event_type="MOBILE_PHONE",
            severity="high",
            evidence_image_base64=_fake_jpeg_base64(),
        ),
        headers=student_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["evidence"] is not None
    assert body["evidence"]["event_id"] == body["id"]


def test_event_source_defaults_to_browser_mediapipe_when_omitted(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()

    payload = _valid_event_payload(session["id"])
    assert "source" not in payload  # this test is only meaningful if source is omitted

    response = client.post(
        "/api/monitoring/events", json=payload, headers=student_headers
    )

    assert response.status_code == 201
    assert response.json()["source"] == "browser_mediapipe"


def test_mobile_phone_event_source_can_be_set_to_browser_yolox(
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
        json=_valid_event_payload(
            session["id"],
            event_type="MOBILE_PHONE",
            severity="high",
            source="browser_yolox",
        ),
        headers=student_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "browser_yolox"

    # And confirm it's actually the persisted value, not just echoed back.
    row = client.get(
        "/api/monitoring/events", headers=admin_headers
    ).json()["items"][0]
    assert row["source"] == "browser_yolox"


# ---------------------------------------------------------------------------
# Phase 2: server-side validation against configured monitoring rules
# ---------------------------------------------------------------------------


def test_event_rejected_when_duration_below_rule_threshold(
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
        json=_valid_event_payload(session["id"], duration_seconds=1.5),
        headers=student_headers,
    )

    assert response.status_code == 422
    assert "below the minimum" in response.json()["detail"]


def test_event_rejected_when_occurrences_below_rule_threshold(
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
        json=_valid_event_payload(session["id"], occurrences=1),
        headers=student_headers,
    )

    assert response.status_code == 422
    assert "below the required" in response.json()["detail"]


def test_event_rejected_when_confidence_below_rule_threshold(
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
        json=_valid_event_payload(session["id"], confidence=0.5),
        headers=student_headers,
    )

    assert response.status_code == 422
    assert "below the threshold" in response.json()["detail"]


def test_event_rejected_when_severity_does_not_match_rule(
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
        json=_valid_event_payload(session["id"], severity="high"),
        headers=student_headers,
    )

    assert response.status_code == 422
    assert "Expected severity" in response.json()["detail"]


def test_event_rejected_when_rule_is_disabled(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)

    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = client.post(
        f"/api/student/exams/{exam['id']}/start", headers=student_headers
    ).json()

    rule = db_session.query(MonitoringRule).filter(
        MonitoringRule.event_type == "HEAD_LEFT"
    ).first()
    rule.is_active = False
    db_session.commit()

    response = client.post(
        "/api/monitoring/events",
        json=_valid_event_payload(session["id"]),
        headers=student_headers,
    )

    assert response.status_code == 422
    assert "currently disabled" in response.json()["detail"]


def test_event_accepted_at_exact_rule_thresholds(
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
        json=_valid_event_payload(
            session["id"],
            confidence=0.75,
            duration_seconds=3.0,
            occurrences=3,
        ),
        headers=student_headers,
    )

    assert response.status_code == 201
