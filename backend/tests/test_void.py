"""Tests for voiding records.

Voiding has to be two things at once, and both are tested here: strong
enough that a stolen session cannot use it, and honest enough that a voided
record is withdrawn from view without becoming unaccountable.
"""

from datetime import datetime

import pytest

from app.core.security import hash_password
from app.core.step_up import MAX_FAILED_ATTEMPTS, step_up_verifier
from app.db.models import (
    AdminAction,
    Evidence,
    Exam,
    ExamSession,
    MonitoringEvent,
    Student,
    User,
)

SYS_PASSWORD = "sysadminpass123"
GOOD_REASON = "Captured a bystander who is not the candidate."


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _clear_step_up_state():
    """Lockout counters live in process memory, so they must not leak
    between tests."""
    step_up_verifier.reset()
    yield
    step_up_verifier.reset()


@pytest.fixture
def system_admin(db_session):
    user = User(
        username="sysadmin",
        password_hash=hash_password(SYS_PASSWORD),
        role="admin",
        status=True,
        is_system_admin=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sys_headers(client, system_admin):
    return _auth_headers(client, "sysadmin", SYS_PASSWORD)


@pytest.fixture
def exam(db_session):
    row = Exam(title="Software Engineering", duration_minutes=60, status="active")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


@pytest.fixture
def session_row(db_session, student_profile, exam):
    row = ExamSession(
        student_id=student_profile.id,
        exam_id=exam.id,
        started_at=datetime.utcnow(),
        status="in_progress",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


@pytest.fixture
def event(db_session, session_row):
    row = MonitoringEvent(
        session_id=session_row.id,
        event_type="FACE_ABSENT",
        confidence=0.9,
        duration_seconds=6.0,
        occurrences=1,
        severity="high",
        status="PENDING_REVIEW",
        detected_at=datetime.utcnow(),
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Who may void
# ---------------------------------------------------------------------------


def test_an_ordinary_admin_cannot_void(client, admin_user, event):
    headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        f"/api/admin/void/events/{event.id}",
        headers=headers,
        json={"password": "adminpass123", "reason": GOOD_REASON},
    )
    assert response.status_code == 403
    assert "system administrator" in response.json()["detail"].lower()


def test_a_student_cannot_void(client, student_user, student_profile, event):
    headers = _auth_headers(client, "student1", "studentpass123")
    response = client.post(
        f"/api/admin/void/events/{event.id}",
        headers=headers,
        json={"password": "studentpass123", "reason": GOOD_REASON},
    )
    assert response.status_code == 403


def test_voiding_requires_authentication(client, event):
    assert (
        client.post(
            f"/api/admin/void/events/{event.id}",
            json={"password": "x", "reason": GOOD_REASON},
        ).status_code
        == 401
    )


# ---------------------------------------------------------------------------
# Step-up authentication
# ---------------------------------------------------------------------------


def test_a_wrong_password_refuses_the_void(client, sys_headers, event, db_session):
    response = client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": "not-my-password", "reason": GOOD_REASON},
    )

    assert response.status_code == 401
    db_session.expire_all()
    assert db_session.get(MonitoringEvent, event.id).voided_at is None


def test_repeated_wrong_passwords_lock_the_action(client, sys_headers, event):
    """Verifying a password on demand is an oracle; it must be bounded."""
    for _ in range(MAX_FAILED_ATTEMPTS):
        client.post(
            f"/api/admin/void/events/{event.id}",
            headers=sys_headers,
            json={"password": "wrong", "reason": GOOD_REASON},
        )

    locked = client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": "wrong", "reason": GOOD_REASON},
    )
    assert locked.status_code == 429
    assert "Retry-After" in locked.headers

    # The lockout holds even against the CORRECT password -- otherwise it
    # would only slow down an attacker who already knows it.
    with_correct = client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )
    assert with_correct.status_code == 429


def test_a_successful_confirmation_clears_earlier_failures(
    client, sys_headers, event, db_session, session_row
):
    second = MonitoringEvent(
        session_id=session_row.id,
        event_type="MOBILE_PHONE",
        confidence=0.9,
        duration_seconds=1.0,
        occurrences=1,
        severity="high",
        status="PENDING_REVIEW",
        detected_at=datetime.utcnow(),
    )
    db_session.add(second)
    db_session.commit()
    db_session.refresh(second)

    for _ in range(MAX_FAILED_ATTEMPTS - 1):
        client.post(
            f"/api/admin/void/events/{event.id}",
            headers=sys_headers,
            json={"password": "wrong", "reason": GOOD_REASON},
        )

    assert (
        client.post(
            f"/api/admin/void/events/{event.id}",
            headers=sys_headers,
            json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
        ).status_code
        == 200
    )
    # The counter reset, so the next mistake does not trip the lockout.
    assert (
        client.post(
            f"/api/admin/void/events/{second.id}",
            headers=sys_headers,
            json={"password": "wrong", "reason": GOOD_REASON},
        ).status_code
        == 401
    )


def test_a_reason_is_mandatory_and_substantive(client, sys_headers, event):
    for reason in ("", "test"):
        response = client.post(
            f"/api/admin/void/events/{event.id}",
            headers=sys_headers,
            json={"password": SYS_PASSWORD, "reason": reason},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Voiding a violation
# ---------------------------------------------------------------------------


def test_voiding_records_who_why_and_when(client, sys_headers, event, db_session):
    response = client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )
    assert response.status_code == 200

    db_session.expire_all()
    voided = db_session.get(MonitoringEvent, event.id)
    assert voided is not None, "the row must survive -- this is not a delete"
    assert voided.voided_at is not None
    assert voided.void_reason == GOOD_REASON


def test_a_voided_violation_leaves_the_review_queue(
    client, sys_headers, event, db_session
):
    before = client.get("/api/monitoring/events", headers=sys_headers).json()
    assert before["total"] == 1

    client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )

    after = client.get("/api/monitoring/events", headers=sys_headers).json()
    assert after["total"] == 0


def test_a_voided_violation_leaves_the_session_rollup_and_its_counts(
    client, sys_headers, event
):
    before = client.get("/api/monitoring/sessions", headers=sys_headers).json()
    assert before["items"][0]["total_events"] == 1

    client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )

    after = client.get("/api/monitoring/sessions", headers=sys_headers).json()
    assert after["total"] == 0


def test_a_voided_violation_leaves_the_dashboard_counts(client, sys_headers, event):
    before = client.get("/api/admin/dashboard/summary", headers=sys_headers).json()
    assert before["total_events"] == 1

    client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )

    after = client.get("/api/admin/dashboard/summary", headers=sys_headers).json()
    assert after["total_events"] == 0


def test_a_voided_violation_leaves_the_case_report(
    client, sys_headers, event, session_row
):
    before = client.get(
        f"/api/reports/sessions/{session_row.id}", headers=sys_headers
    ).json()
    assert before["total_events"] == 1

    client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )

    after = client.get(
        f"/api/reports/sessions/{session_row.id}", headers=sys_headers
    ).json()
    assert after["total_events"] == 0
    assert after["events"] == []


def test_a_voided_violation_takes_its_evidence_and_decisions_with_it(
    client, sys_headers, event, db_session, system_admin
):
    db_session.add(
        Evidence(
            event_id=event.id,
            image_path="2026/09/07/EVT-000001.jpg",
            captured_at=datetime.utcnow(),
            metadata_json={"content_type": "image/jpeg", "size_bytes": 10},
        )
    )
    db_session.add(
        AdminAction(
            event_id=event.id,
            admin_id=system_admin.id,
            action="CONFIRMED",
            reason="Reviewed",
        )
    )
    db_session.commit()

    assert client.get("/api/evidence", headers=sys_headers).json()["total"] == 1
    assert client.get("/api/audit", headers=sys_headers).json()["total"] == 1

    client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )

    assert client.get("/api/evidence", headers=sys_headers).json()["total"] == 0
    assert client.get("/api/audit", headers=sys_headers).json()["total"] == 0


def test_a_violation_cannot_be_voided_twice(client, sys_headers, event):
    client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )
    repeat = client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )
    assert repeat.status_code == 409


def test_an_unknown_violation_is_a_404(client, sys_headers):
    assert (
        client.post(
            "/api/admin/void/events/999999",
            headers=sys_headers,
            json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
        ).status_code
        == 404
    )


# ---------------------------------------------------------------------------
# The safeguard: evidence behind a live punishment
# ---------------------------------------------------------------------------


def test_a_violation_backing_an_active_block_cannot_be_voided(
    client, sys_headers, event, session_row
):
    """Removing the justification for a punishment still in force would
    leave the institution unable to account for it."""
    created = client.post(
        "/api/enforcement/actions",
        headers=sys_headers,
        json={
            "session_id": session_row.id,
            "action_type": "BLOCK",
            "reason": "Phone visible in evidence",
            "block_minutes": 10,
            "event_id": event.id,
        },
    )
    assert created.status_code == 201

    response = client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )

    assert response.status_code == 409
    assert "active enforcement" in response.json()["detail"].lower()


def test_the_violation_can_be_voided_once_the_block_is_lifted(
    client, sys_headers, event, session_row
):
    created = client.post(
        "/api/enforcement/actions",
        headers=sys_headers,
        json={
            "session_id": session_row.id,
            "action_type": "BLOCK",
            "reason": "Phone visible in evidence",
            "block_minutes": 10,
            "event_id": event.id,
        },
    ).json()
    client.post(f"/api/enforcement/actions/{created['id']}/lift", headers=sys_headers)

    response = client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Voiding an exam
# ---------------------------------------------------------------------------


def test_an_exam_with_no_attempts_can_be_voided(client, sys_headers, exam, db_session):
    response = client.post(
        f"/api/admin/void/exams/{exam.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": "Created in error during setup."},
    )
    assert response.status_code == 200

    db_session.expire_all()
    assert db_session.get(Exam, exam.id).voided_at is not None
    assert client.get("/api/exams", headers=sys_headers).json() == []


def test_an_exam_with_attempts_cannot_be_voided(
    client, sys_headers, exam, session_row
):
    """Voiding it would withdraw real student attempts and everything
    recorded against them."""
    response = client.post(
        f"/api/admin/void/exams/{exam.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": "Created in error during setup."},
    )

    assert response.status_code == 409
    assert "attempt" in response.json()["detail"].lower()


def test_a_voided_exam_disappears_for_students(
    client, sys_headers, exam, student_user, student_profile
):
    student_headers = _auth_headers(client, "student1", "studentpass123")
    assert len(client.get("/api/student/exams", headers=student_headers).json()) == 1

    client.post(
        f"/api/admin/void/exams/{exam.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": "Created in error during setup."},
    )

    assert client.get("/api/student/exams", headers=student_headers).json() == []
    assert (
        client.get(f"/api/student/exams/{exam.id}", headers=student_headers).status_code
        == 404
    )


# ---------------------------------------------------------------------------
# Accountability: voided is not the same as gone
# ---------------------------------------------------------------------------


def test_voided_records_remain_listed_for_the_system_admin(
    client, sys_headers, event, exam, db_session
):
    """Without this view, voiding would be indistinguishable from deletion
    to anyone auditing the system."""
    client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )

    body = client.get("/api/admin/void", headers=sys_headers).json()

    assert body["total"] == 1
    record = body["items"][0]
    assert record["kind"] == "monitoring_event"
    assert record["voided_by"] == "sysadmin"
    assert record["void_reason"] == GOOD_REASON


def test_an_ordinary_admin_cannot_read_the_voided_list(client, admin_user, event):
    headers = _auth_headers(client, "admin1", "adminpass123")
    assert client.get("/api/admin/void", headers=headers).status_code == 403


def test_no_response_ever_echoes_the_password(client, sys_headers, event):
    response = client.post(
        f"/api/admin/void/events/{event.id}",
        headers=sys_headers,
        json={"password": SYS_PASSWORD, "reason": GOOD_REASON},
    )
    assert SYS_PASSWORD not in response.text

    listing = client.get("/api/admin/void", headers=sys_headers)
    assert SYS_PASSWORD not in listing.text
