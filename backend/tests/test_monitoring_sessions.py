"""Tests for the session-level monitoring rollup.

The rollup is a query-time grouping: these tests assert the combined view
is correct AND that the underlying per-event rows are left untouched, since
each event's own evidence is what the whole system exists to produce.
"""

from datetime import datetime, timedelta

import pytest

from app.db.models import Exam, ExamSession, MonitoringEvent, Student, User
from app.core.security import hash_password


# Defined locally rather than imported from tests/conftest.py, matching
# tests/test_enforcement.py. Importing conftest as `tests.conftest` loads a
# SECOND copy of that module, which re-runs its module-level
# app.dependency_overrides assignment and rebinds the app to a different
# in-memory engine -- one the autouse table-creation fixture never touches,
# so every test in the run then fails with "no such table".
def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(client, admin_user):
    return _auth_headers(client, "admin1", "adminpass123")


def _make_student(db_session, username, code, full_name):
    user = User(
        username=username,
        password_hash=hash_password("studentpass123"),
        role="student",
        status=True,
    )
    db_session.add(user)
    db_session.flush()
    student = Student(
        user_id=user.id, student_id=code, full_name=full_name, is_active=True
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


def _make_session(db_session, student, exam, status="in_progress"):
    row = ExamSession(
        student_id=student.id,
        exam_id=exam.id,
        started_at=datetime.utcnow(),
        status=status,
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
    status="PENDING_REVIEW",
    minutes_ago=0,
):
    event = MonitoringEvent(
        session_id=session_row.id,
        event_type=event_type,
        confidence=0.9,
        duration_seconds=6.0,
        occurrences=1,
        severity=severity,
        status=status,
        detected_at=datetime.utcnow() - timedelta(minutes=minutes_ago),
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


@pytest.fixture
def exam(db_session):
    row = Exam(title="CS", duration_minutes=60, status="active")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_unauthenticated_request_is_rejected(client):
    assert client.get("/api/monitoring/sessions").status_code == 401


def test_student_cannot_list_monitoring_sessions(client, student_user, student_profile):
    headers = _auth_headers(client, "student1", "studentpass123")
    assert client.get("/api/monitoring/sessions", headers=headers).status_code == 403


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def test_repeated_violations_collapse_into_one_session_row(
    client, admin_headers, db_session, student_profile, exam
):
    """Three FACE_ABSENT plus two MOBILE_PHONE is ONE row, not five."""
    session_row = _make_session(db_session, student_profile, exam)
    for _ in range(3):
        _add_event(db_session, session_row, event_type="FACE_ABSENT")
    for _ in range(2):
        _add_event(db_session, session_row, event_type="MOBILE_PHONE")

    body = client.get("/api/monitoring/sessions", headers=admin_headers).json()

    assert body["total"] == 1
    item = body["items"][0]
    assert item["session_id"] == session_row.id
    assert item["total_events"] == 5
    assert item["events_by_type"] == {"FACE_ABSENT": 3, "MOBILE_PHONE": 2}


def test_mixed_activity_types_are_broken_down_separately(
    client, admin_headers, db_session, student_profile, exam
):
    session_row = _make_session(db_session, student_profile, exam)
    _add_event(db_session, session_row, event_type="FACE_ABSENT")
    _add_event(db_session, session_row, event_type="LOOKING_AWAY", severity="medium")
    _add_event(db_session, session_row, event_type="MOBILE_PHONE")
    _add_event(db_session, session_row, event_type="MOBILE_PHONE")

    item = client.get("/api/monitoring/sessions", headers=admin_headers).json()["items"][0]

    assert item["events_by_type"] == {
        "FACE_ABSENT": 1,
        "LOOKING_AWAY": 1,
        "MOBILE_PHONE": 2,
    }
    assert item["total_events"] == 4
    assert item["high_severity_events"] == 3


def test_review_status_counts_are_reported_per_session(
    client, admin_headers, db_session, student_profile, exam
):
    session_row = _make_session(db_session, student_profile, exam)
    _add_event(db_session, session_row, status="PENDING_REVIEW")
    _add_event(db_session, session_row, status="PENDING_REVIEW")
    _add_event(db_session, session_row, status="CONFIRMED")
    _add_event(db_session, session_row, status="IGNORED")

    item = client.get("/api/monitoring/sessions", headers=admin_headers).json()["items"][0]

    assert item["pending_events"] == 2
    assert item["confirmed_events"] == 1
    assert item["ignored_events"] == 1


def test_student_and_exam_context_is_joined_in(
    client, admin_headers, db_session, student_profile, exam
):
    session_row = _make_session(db_session, student_profile, exam)
    _add_event(db_session, session_row)

    item = client.get("/api/monitoring/sessions", headers=admin_headers).json()["items"][0]

    assert item["student_full_name"] == "Test Student"
    assert item["student_id"] == "STU-1001"
    assert item["exam_title"] == "CS"
    assert item["exam_id"] == exam.id
    assert item["session_status"] == "in_progress"


def test_first_and_last_detected_span_the_session(
    client, admin_headers, db_session, student_profile, exam
):
    session_row = _make_session(db_session, student_profile, exam)
    _add_event(db_session, session_row, minutes_ago=30)
    _add_event(db_session, session_row, minutes_ago=0)

    item = client.get("/api/monitoring/sessions", headers=admin_headers).json()["items"][0]

    assert item["first_detected_at"] < item["last_detected_at"]


def test_separate_sessions_stay_separate_rows(
    client, admin_headers, db_session, student_profile, exam
):
    """Two students' sessions must never be combined into one record."""
    other = _make_student(db_session, "student2", "STU-1002", "Second Student")
    first = _make_session(db_session, student_profile, exam)
    second = _make_session(db_session, other, exam)
    _add_event(db_session, first)
    _add_event(db_session, second)

    body = client.get("/api/monitoring/sessions", headers=admin_headers).json()

    assert body["total"] == 2
    assert {i["session_id"] for i in body["items"]} == {first.id, second.id}


def test_sessions_without_events_are_absent(
    client, admin_headers, db_session, student_profile, exam
):
    _make_session(db_session, student_profile, exam)

    body = client.get("/api/monitoring/sessions", headers=admin_headers).json()

    assert body["total"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def test_event_type_filter_scopes_the_counts(
    client, admin_headers, db_session, student_profile, exam
):
    session_row = _make_session(db_session, student_profile, exam)
    _add_event(db_session, session_row, event_type="FACE_ABSENT")
    _add_event(db_session, session_row, event_type="MOBILE_PHONE")
    _add_event(db_session, session_row, event_type="MOBILE_PHONE")

    item = client.get(
        "/api/monitoring/sessions",
        headers=admin_headers,
        params={"event_type": "MOBILE_PHONE"},
    ).json()["items"][0]

    assert item["total_events"] == 2
    assert item["events_by_type"] == {"MOBILE_PHONE": 2}


def test_filter_drops_sessions_with_no_matching_events(
    client, admin_headers, db_session, student_profile, exam
):
    session_row = _make_session(db_session, student_profile, exam)
    _add_event(db_session, session_row, event_type="FACE_ABSENT")

    body = client.get(
        "/api/monitoring/sessions",
        headers=admin_headers,
        params={"event_type": "MOBILE_PHONE"},
    ).json()

    assert body["total"] == 0


def test_status_and_severity_filters(
    client, admin_headers, db_session, student_profile, exam
):
    session_row = _make_session(db_session, student_profile, exam)
    _add_event(db_session, session_row, status="CONFIRMED", severity="high")
    _add_event(
        db_session,
        session_row,
        status="PENDING_REVIEW",
        severity="medium",
        event_type="HEAD_LEFT",
    )

    confirmed = client.get(
        "/api/monitoring/sessions", headers=admin_headers, params={"status": "CONFIRMED"}
    ).json()["items"][0]
    assert confirmed["total_events"] == 1

    medium = client.get(
        "/api/monitoring/sessions", headers=admin_headers, params={"severity": "medium"}
    ).json()["items"][0]
    assert medium["total_events"] == 1
    assert medium["high_severity_events"] == 0


def test_search_matches_student_name_and_code(
    client, admin_headers, db_session, student_profile, exam
):
    other = _make_student(db_session, "student3", "STU-2002", "Zara Ahmed")
    _add_event(db_session, _make_session(db_session, student_profile, exam))
    _add_event(db_session, _make_session(db_session, other, exam))

    by_name = client.get(
        "/api/monitoring/sessions", headers=admin_headers, params={"search": "Zara"}
    ).json()
    assert by_name["total"] == 1
    assert by_name["items"][0]["student_full_name"] == "Zara Ahmed"

    by_code = client.get(
        "/api/monitoring/sessions", headers=admin_headers, params={"search": "STU-1001"}
    ).json()
    assert by_code["total"] == 1
    assert by_code["items"][0]["student_id"] == "STU-1001"


def test_exam_and_session_status_filters(
    client, admin_headers, db_session, student_profile, exam
):
    other_exam = Exam(title="Physics", duration_minutes=30, status="active")
    db_session.add(other_exam)
    db_session.commit()
    db_session.refresh(other_exam)

    _add_event(db_session, _make_session(db_session, student_profile, exam))
    other_student = _make_student(db_session, "student4", "STU-3003", "Third Student")
    _add_event(
        db_session,
        _make_session(db_session, other_student, other_exam, status="submitted"),
    )

    by_exam = client.get(
        "/api/monitoring/sessions", headers=admin_headers, params={"exam_id": exam.id}
    ).json()
    assert by_exam["total"] == 1
    assert by_exam["items"][0]["exam_title"] == "CS"

    by_state = client.get(
        "/api/monitoring/sessions",
        headers=admin_headers,
        params={"session_status": "submitted"},
    ).json()
    assert by_state["total"] == 1
    assert by_state["items"][0]["session_status"] == "submitted"


# ---------------------------------------------------------------------------
# Pagination and ordering
# ---------------------------------------------------------------------------


def test_pagination_counts_sessions_not_events(
    client, admin_headers, db_session, student_profile, exam
):
    """total must be the number of session rows, not underlying events."""
    session_row = _make_session(db_session, student_profile, exam)
    for _ in range(7):
        _add_event(db_session, session_row)

    body = client.get(
        "/api/monitoring/sessions", headers=admin_headers, params={"page_size": 20}
    ).json()

    assert body["total"] == 1
    assert body["total_pages"] == 1
    assert body["items"][0]["total_events"] == 7


def test_most_recently_active_session_is_listed_first(
    client, admin_headers, db_session, student_profile, exam
):
    other = _make_student(db_session, "student5", "STU-4004", "Recent Student")
    older = _make_session(db_session, student_profile, exam)
    newer = _make_session(db_session, other, exam)
    _add_event(db_session, older, minutes_ago=45)
    _add_event(db_session, newer, minutes_ago=1)

    items = client.get("/api/monitoring/sessions", headers=admin_headers).json()["items"]

    assert items[0]["session_id"] == newer.id


# ---------------------------------------------------------------------------
# The rollup must not disturb the underlying records
# ---------------------------------------------------------------------------


def test_individual_events_remain_listable_and_unmerged(
    client, admin_headers, db_session, student_profile, exam
):
    session_row = _make_session(db_session, student_profile, exam)
    for _ in range(3):
        _add_event(db_session, session_row, event_type="FACE_ABSENT")

    rollup = client.get("/api/monitoring/sessions", headers=admin_headers).json()
    assert rollup["items"][0]["total_events"] == 3

    # The per-event endpoint still returns all three separate rows, each
    # keeping its own identity for evidence review.
    events = client.get(
        "/api/monitoring/events",
        headers=admin_headers,
        params={"session_id": session_row.id},
    ).json()
    assert events["total"] == 3
    assert len({item["id"] for item in events["items"]}) == 3
    assert db_session.query(MonitoringEvent).count() == 3
