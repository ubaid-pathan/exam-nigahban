"""Tests for the per-session case report.

This document can end up in a student's academic file, so the tests below
check more than shape: that every decision is preserved and attributed,
that the report never asserts wrongdoing on its own, and that it stays
admin-only.
"""

from datetime import datetime, timedelta

import pytest

from app.core.security import hash_password
from app.db.models import (
    AdminAction,
    Evidence,
    Exam,
    ExamSession,
    MonitoringEvent,
    Student,
    User,
)


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(client, admin_user):
    return _auth_headers(client, "admin1", "adminpass123")


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


def _add_event(
    db_session,
    session_row,
    event_type="FACE_ABSENT",
    severity="high",
    event_status="PENDING_REVIEW",
    minutes_ago=0,
    with_evidence=False,
):
    event = MonitoringEvent(
        session_id=session_row.id,
        event_type=event_type,
        confidence=0.9,
        duration_seconds=6.0,
        occurrences=1,
        severity=severity,
        status=event_status,
        detected_at=datetime.utcnow() - timedelta(minutes=minutes_ago),
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    if with_evidence:
        evidence = Evidence(
            event_id=event.id,
            image_path="2026/09/06/EVT-000001.jpg",
            captured_at=datetime.utcnow(),
            metadata_json={"content_type": "image/jpeg", "size_bytes": 100},
        )
        db_session.add(evidence)
        db_session.commit()
    return event


def _add_decision(db_session, event, admin, action="CONFIRMED", reason="Clear view"):
    row = AdminAction(
        event_id=event.id, admin_id=admin.id, action=action, reason=reason
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_unauthenticated_request_is_rejected(client, session_row):
    assert client.get(f"/api/reports/sessions/{session_row.id}").status_code == 401


def test_student_cannot_generate_a_report(
    client, student_user, student_profile, session_row
):
    """A candidate must never be able to read the case built about them."""
    headers = _auth_headers(client, "student1", "studentpass123")
    assert (
        client.get(f"/api/reports/sessions/{session_row.id}", headers=headers).status_code
        == 403
    )


def test_unknown_session_returns_404(client, admin_headers):
    assert client.get("/api/reports/sessions/999999", headers=admin_headers).status_code == 404


# ---------------------------------------------------------------------------
# Identity and provenance
# ---------------------------------------------------------------------------


def test_report_carries_student_program_and_section(
    client, admin_headers, db_session, student_profile, session_row
):
    body = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).json()

    assert body["student"]["full_name"] == "Test Student"
    assert body["student"]["student_id"] == "STU-1001"
    assert body["student"]["department"] == "Computer Science"
    assert body["student"]["class_name"] == "CS-101"


def test_report_records_who_generated_it_and_when(
    client, admin_headers, session_row
):
    """A disciplinary document must be attributable and dated: the
    underlying data keeps changing as reviews happen."""
    body = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).json()

    assert body["generated_by"] == "admin1"
    assert body["generated_at"] is not None


def test_report_handles_a_student_with_no_program_or_section(
    client, admin_headers, db_session, student_profile, session_row
):
    student_profile.department = None
    student_profile.class_name = None
    db_session.commit()

    body = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).json()

    assert body["student"]["department"] is None
    assert body["student"]["class_name"] is None


def test_report_includes_exam_and_session_context(
    client, admin_headers, db_session, session_row, exam
):
    session_row.status = "cancelled"
    session_row.score = 0
    session_row.ended_at = datetime.utcnow()
    db_session.commit()

    body = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).json()

    assert body["exam"]["title"] == "Software Engineering"
    assert body["session"]["status"] == "cancelled"
    assert body["session"]["score"] == 0
    assert body["session"]["ended_at"] is not None


# ---------------------------------------------------------------------------
# Flagged activity
# ---------------------------------------------------------------------------


def test_report_lists_every_flagged_activity_chronologically(
    client, admin_headers, db_session, session_row
):
    _add_event(db_session, session_row, event_type="MOBILE_PHONE", minutes_ago=5)
    _add_event(db_session, session_row, event_type="FACE_ABSENT", minutes_ago=30)

    body = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).json()

    assert body["total_events"] == 2
    # A case is read as a sequence, so oldest first.
    assert [e["event_type"] for e in body["events"]] == ["FACE_ABSENT", "MOBILE_PHONE"]


def test_report_counts_activity_by_review_status_and_severity(
    client, admin_headers, db_session, session_row
):
    _add_event(db_session, session_row, event_status="CONFIRMED", severity="high")
    _add_event(db_session, session_row, event_status="CONFIRMED", severity="high")
    _add_event(db_session, session_row, event_status="IGNORED", severity="medium")
    _add_event(db_session, session_row, event_status="PENDING_REVIEW", severity="medium")

    body = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).json()

    assert body["total_events"] == 4
    assert body["confirmed_events"] == 2
    assert body["ignored_events"] == 1
    assert body["pending_events"] == 1
    assert body["high_severity_events"] == 2


def test_report_reports_whether_evidence_exists_for_each_activity(
    client, admin_headers, db_session, session_row
):
    _add_event(db_session, session_row, with_evidence=True)
    _add_event(db_session, session_row, event_type="HEAD_LEFT", severity="medium")

    body = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).json()

    evidence_ids = [e["evidence_id"] for e in body["events"]]
    assert evidence_ids.count(None) == 1
    assert sum(1 for i in evidence_ids if i is not None) == 1


def test_report_never_exposes_the_evidence_file_path(
    client, admin_headers, db_session, session_row
):
    _add_event(db_session, session_row, with_evidence=True)

    raw = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).text

    assert "image_path" not in raw
    assert ".jpg" not in raw


# ---------------------------------------------------------------------------
# Decisions: the half that makes the document defensible
# ---------------------------------------------------------------------------


def test_each_activity_carries_its_administrator_decision(
    client, admin_headers, db_session, admin_user, session_row
):
    event = _add_event(db_session, session_row, event_status="CONFIRMED")
    _add_decision(db_session, event, admin_user, "CONFIRMED", "Face not visible")

    body = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).json()
    decisions = body["events"][0]["decisions"]

    assert len(decisions) == 1
    assert decisions[0]["action"] == "CONFIRMED"
    assert decisions[0]["reason"] == "Face not visible"
    assert decisions[0]["admin_username"] == "admin1"


def test_a_reversed_decision_keeps_both_entries_in_order(
    client, admin_headers, db_session, admin_user, session_row
):
    """The audit trail is append-only, so a reversal must appear as a
    second entry rather than replacing the first."""
    event = _add_event(db_session, session_row, event_status="IGNORED")
    _add_decision(db_session, event, admin_user, "CONFIRMED", "Initial call")
    _add_decision(db_session, event, admin_user, "IGNORED", "Reviewed again")

    body = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).json()
    decisions = body["events"][0]["decisions"]

    assert [d["action"] for d in decisions] == ["CONFIRMED", "IGNORED"]
    assert [d["reason"] for d in decisions] == ["Initial call", "Reviewed again"]


def test_an_unreviewed_activity_has_no_decisions(
    client, admin_headers, db_session, session_row
):
    _add_event(db_session, session_row, event_status="PENDING_REVIEW")

    body = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).json()

    assert body["events"][0]["decisions"] == []


# ---------------------------------------------------------------------------
# Enforcement
# ---------------------------------------------------------------------------


def test_report_includes_enforcement_actions_with_their_reasons(
    client, admin_headers, db_session, admin_user, student_profile, session_row
):
    client.post(
        "/api/enforcement/actions",
        headers=admin_headers,
        json={
            "session_id": session_row.id,
            "action_type": "CANCEL_EXAM",
            "reason": "Repeated confirmed violations",
        },
    )

    body = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).json()
    actions = body["enforcement_actions"]

    assert len(actions) == 1
    assert actions[0]["action_type"] == "CANCEL_EXAM"
    assert actions[0]["reason"] == "Repeated confirmed violations"
    assert actions[0]["admin_username"] == "admin1"
    assert actions[0]["effective_status"] == "COMPLETED"


def test_a_clean_session_produces_an_empty_but_valid_report(
    client, admin_headers, session_row
):
    """A student with no flagged activity must still produce a report --
    that is the document proving nothing was found."""
    body = client.get(f"/api/reports/sessions/{session_row.id}", headers=admin_headers).json()

    assert body["total_events"] == 0
    assert body["events"] == []
    assert body["enforcement_actions"] == []
    assert body["student"]["full_name"] == "Test Student"


# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------


def test_report_never_asserts_wrongdoing(
    client, admin_headers, db_session, admin_user, session_row
):
    """The system records that an activity was
    flagged and that a human decided about it -- never that a student
    cheated."""
    event = _add_event(db_session, session_row, event_status="CONFIRMED")
    _add_decision(db_session, event, admin_user)

    raw = client.get(
        f"/api/reports/sessions/{session_row.id}", headers=admin_headers
    ).text.lower()

    for banned in ["cheat", "guilty", "culprit", "offender"]:
        assert banned not in raw
