from datetime import datetime, timedelta

from app.core.security import hash_password
from app.db.models import AdminAction, ExamSession, Student, User


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


def _create_active_exam(client, admin_headers, title="Sample Exam", duration_minutes=30):
    payload = {
        "title": title,
        "description": "A sample exam",
        "duration_minutes": duration_minutes,
    }
    exam = client.post("/api/exams", json=payload, headers=admin_headers).json()
    client.patch(
        f"/api/exams/{exam['id']}/status", json={"status": "active"}, headers=admin_headers
    )
    return exam


def _start_session(client, student_headers, exam_id):
    return client.post(
        f"/api/student/exams/{exam_id}/start", headers=student_headers
    ).json()


def _event_payload(session_id, **overrides):
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


def _fake_jpeg_base64() -> str:
    import base64

    return base64.b64encode(b"\xff\xd8\xff" + b"\x00" * 64).decode("ascii")


def _create_event(client, student_headers, session_id, with_evidence=False, **overrides):
    payload = _event_payload(session_id, **overrides)
    if with_evidence:
        payload["evidence_image_base64"] = _fake_jpeg_base64()
    return client.post(
        "/api/monitoring/events",
        json=payload,
        headers=student_headers,
    ).json()


def _review(client, admin_headers, evidence_id, action, reason=None):
    body = {"action": action}
    if reason is not None:
        body["reason"] = reason
    return client.post(
        f"/api/evidence/{evidence_id}/review",
        json=body,
        headers=admin_headers,
    )


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_admin_can_retrieve_summary(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "active_exams",
        "active_sessions",
        "active_students",
        "total_events",
        "pending_review_events",
        "confirmed_events",
        "ignored_events",
        "high_severity_pending_events",
        "evidence_count",
        "total_review_actions",
        "generated_at",
    }


def test_unauthenticated_request_returns_401(client):
    response = client.get("/api/admin/dashboard/summary")
    assert response.status_code == 401


def test_student_request_returns_403(client, admin_user, student_user, student_profile):
    student_headers = _auth_headers(client, "student1", "studentpass123")
    response = client.get("/api/admin/dashboard/summary", headers=student_headers)
    assert response.status_code == 403


def test_empty_database_returns_all_zero_counts(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["active_exams"] == 0
    assert body["active_sessions"] == 0
    assert body["active_students"] == 0
    assert body["total_events"] == 0
    assert body["pending_review_events"] == 0
    assert body["confirmed_events"] == 0
    assert body["ignored_events"] == 0
    assert body["high_severity_pending_events"] == 0
    assert body["evidence_count"] == 0
    assert body["total_review_actions"] == 0


# ---------------------------------------------------------------------------
# active_exams / active_sessions / active_students
# ---------------------------------------------------------------------------


def test_active_exams_counts_only_active_status(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    active_exam = _create_active_exam(client, admin_headers, title="Active Exam")

    draft_payload = {"title": "Draft Exam", "description": None, "duration_minutes": 20}
    client.post("/api/exams", json=draft_payload, headers=admin_headers)

    inactive_exam = _create_active_exam(client, admin_headers, title="Inactive Exam")
    client.patch(
        f"/api/exams/{inactive_exam['id']}/status",
        json={"status": "inactive"},
        headers=admin_headers,
    )

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    assert response.json()["active_exams"] == 1


def test_active_session_counted_when_genuinely_in_progress(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    _start_session(client, student_headers, exam["id"])

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    body = response.json()
    assert body["active_sessions"] == 1
    assert body["active_students"] == 1


def test_stale_in_progress_session_past_deadline_excluded(
    client, admin_user, student_user, student_profile, db_session
):
    """The key lazy-expiry edge case: a session still marked "in_progress"
    in the database because nothing has touched it since its deadline
    passed must NOT be counted as active by this read-only endpoint."""
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers, duration_minutes=30)
    session = _start_session(client, student_headers, exam["id"])

    row = db_session.get(ExamSession, session["id"])
    row.started_at = datetime.utcnow() - timedelta(minutes=60)
    db_session.commit()
    assert row.status == "in_progress"  # still stale in the DB, untouched

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    body = response.json()
    assert body["active_sessions"] == 0
    assert body["active_students"] == 0

    # This endpoint must not have mutated the stale row as a side effect.
    db_session.refresh(row)
    assert row.status == "in_progress"


def test_submitted_session_not_counted_as_active(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])
    client.post(f"/api/student/sessions/{session['id']}/submit", headers=student_headers)

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    body = response.json()
    assert body["active_sessions"] == 0
    assert body["active_students"] == 0


def test_active_sessions_can_exceed_active_students(
    client, admin_user, student_user, student_profile
):
    """A single student with two concurrent sessions across two different
    active exams is not prevented by the uniqueness rule (which is
    per-exam), so active_sessions may legitimately exceed active_students."""
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam_a = _create_active_exam(client, admin_headers, title="Exam A")
    exam_b = _create_active_exam(client, admin_headers, title="Exam B")
    _start_session(client, student_headers, exam_a["id"])
    _start_session(client, student_headers, exam_b["id"])

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    body = response.json()
    assert body["active_sessions"] == 2
    assert body["active_students"] == 1


# ---------------------------------------------------------------------------
# Event status / severity counts
# ---------------------------------------------------------------------------


def test_pending_review_events_counts_only_pending(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])
    _create_event(client, student_headers, session["id"])
    _create_event(client, student_headers, session["id"])

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    assert response.json()["pending_review_events"] == 2


def test_confirmed_and_ignored_events_reflect_reviews(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])

    confirmed_event = _create_event(client, student_headers, session["id"], with_evidence=True)
    ignored_event = _create_event(client, student_headers, session["id"], with_evidence=True)
    _create_event(client, student_headers, session["id"])  # left pending

    _review(client, admin_headers, confirmed_event["evidence"]["id"], "CONFIRMED")
    _review(client, admin_headers, ignored_event["evidence"]["id"], "IGNORED")

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    body = response.json()
    assert body["confirmed_events"] == 1
    assert body["ignored_events"] == 1
    assert body["pending_review_events"] == 1
    assert body["total_events"] == 3


def test_high_severity_pending_excludes_reviewed_events(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])

    still_pending_high = _create_event(client, student_headers, session["id"], severity="high")
    reviewed_high = _create_event(
        client, student_headers, session["id"], severity="high", with_evidence=True
    )
    _create_event(client, student_headers, session["id"], severity="low")

    _review(client, admin_headers, reviewed_high["evidence"]["id"], "CONFIRMED")

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    assert response.json()["high_severity_pending_events"] == 1


def test_total_events_sums_all_statuses(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])

    for _ in range(4):
        _create_event(client, student_headers, session["id"])

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    assert response.json()["total_events"] == 4


def test_evidence_count_reflects_created_evidence(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])

    _create_event(client, student_headers, session["id"], with_evidence=True)
    _create_event(client, student_headers, session["id"], with_evidence=True)
    _create_event(client, student_headers, session["id"])  # no evidence

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    assert response.json()["evidence_count"] == 2


# ---------------------------------------------------------------------------
# total_review_actions (explicitly requested checks)
# ---------------------------------------------------------------------------


def test_total_review_actions_equals_admin_action_row_count(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])

    event_a = _create_event(client, student_headers, session["id"], with_evidence=True)
    event_b = _create_event(client, student_headers, session["id"], with_evidence=True)

    _review(client, admin_headers, event_a["evidence"]["id"], "CONFIRMED")
    _review(client, admin_headers, event_b["evidence"]["id"], "IGNORED")

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    body = response.json()

    admin_action_row_count = db_session.query(AdminAction).count()
    assert admin_action_row_count == 2
    assert body["total_review_actions"] == admin_action_row_count


def test_repeated_reviews_of_same_event_each_increase_total_review_actions(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])
    event = _create_event(client, student_headers, session["id"], with_evidence=True)
    evidence_id = event["evidence"]["id"]

    before = client.get("/api/admin/dashboard/summary", headers=admin_headers).json()
    assert before["total_review_actions"] == 0

    _review(client, admin_headers, evidence_id, "CONFIRMED")
    after_first = client.get("/api/admin/dashboard/summary", headers=admin_headers).json()
    assert after_first["total_review_actions"] == 1

    _review(client, admin_headers, evidence_id, "IGNORED", reason="Reconsidered")
    after_second = client.get("/api/admin/dashboard/summary", headers=admin_headers).json()
    assert after_second["total_review_actions"] == 2

    _review(client, admin_headers, evidence_id, "IGNORED")
    after_third = client.get("/api/admin/dashboard/summary", headers=admin_headers).json()
    assert after_third["total_review_actions"] == 3

    # Reviewing the SAME event three times still only ever produces one
    # current MonitoringEvent status, not three -- confirming
    # total_review_actions (audit-log rows) is distinct from event-status
    # counts (confirmed_events + ignored_events).
    assert after_third["confirmed_events"] + after_third["ignored_events"] == 1


def test_response_does_not_contain_total_admin_actions(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])
    event = _create_event(client, student_headers, session["id"], with_evidence=True)
    _review(client, admin_headers, event["evidence"]["id"], "CONFIRMED")

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    body = response.json()

    assert "total_admin_actions" not in body
    assert "total_review_actions" in body


# ---------------------------------------------------------------------------
# No sensitive data leakage
# ---------------------------------------------------------------------------


def test_response_never_leaks_sensitive_fields(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])
    event = _create_event(client, student_headers, session["id"], with_evidence=True)
    _review(client, admin_headers, event["evidence"]["id"], "CONFIRMED")

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    body = response.json()

    assert "password_hash" not in body
    assert "image_path" not in body
    assert all(isinstance(value, (int, str)) for value in body.values())


# ---------------------------------------------------------------------------
# Regression: existing endpoints unaffected
# ---------------------------------------------------------------------------


def test_existing_review_and_listing_endpoints_still_work(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])
    event = _create_event(client, student_headers, session["id"], with_evidence=True)

    review_response = _review(client, admin_headers, event["evidence"]["id"], "CONFIRMED")
    assert review_response.status_code == 200

    listing_response = client.get("/api/monitoring/events", headers=admin_headers)
    assert listing_response.status_code == 200
    assert listing_response.json()["total"] == 1
