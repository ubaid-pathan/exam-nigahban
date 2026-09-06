"""Tests for the cohort roster report and its CSV export.

The property that matters most here, and is easiest to get wrong, is that a
candidate who was monitored and produced NOTHING still appears. A cohort
report that only lists offenders cannot answer "was this section
monitored", which is most of what it is for.
"""

import csv
import io
from datetime import datetime, timedelta

import pytest

from app.core.security import hash_password
from app.db.models import Exam, ExamSession, MonitoringEvent, Student, User


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


def _make_student(db_session, username, code, name, department, class_name):
    user = User(
        username=username,
        password_hash=hash_password("studentpass123"),
        role="student",
        status=True,
    )
    db_session.add(user)
    db_session.flush()
    student = Student(
        user_id=user.id,
        student_id=code,
        full_name=name,
        department=department,
        class_name=class_name,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


def _make_session(db_session, student, exam, status="submitted"):
    row = ExamSession(
        student_id=student.id,
        exam_id=exam.id,
        started_at=datetime.utcnow() - timedelta(minutes=30),
        status=status,
        score=70,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _add_event(db_session, session_row, severity="high", status="PENDING_REVIEW"):
    event = MonitoringEvent(
        session_id=session_row.id,
        event_type="FACE_ABSENT",
        confidence=0.9,
        duration_seconds=6.0,
        occurrences=1,
        severity=severity,
        status=status,
        detected_at=datetime.utcnow(),
    )
    db_session.add(event)
    db_session.commit()
    return event


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_roster_endpoints_are_admin_only(client, student_user, student_profile):
    headers = _auth_headers(client, "student1", "studentpass123")
    assert client.get("/api/reports/roster", headers=headers).status_code == 403
    assert client.get("/api/reports/roster.csv", headers=headers).status_code == 403
    assert client.get("/api/reports/roster/filters", headers=headers).status_code == 403


def test_roster_rejects_unauthenticated_requests(client):
    assert client.get("/api/reports/roster").status_code == 401
    assert client.get("/api/reports/roster.csv").status_code == 401


# ---------------------------------------------------------------------------
# The defining property: clean candidates still appear
# ---------------------------------------------------------------------------


def test_a_session_with_no_flagged_activity_still_appears(
    client, admin_headers, db_session, exam
):
    student = _make_student(db_session, "s1", "SE-001", "Clean Candidate", "SE", "D")
    _make_session(db_session, student, exam)

    body = client.get("/api/reports/roster", headers=admin_headers).json()

    assert body["total"] == 1
    row = body["items"][0]
    assert row["student_full_name"] == "Clean Candidate"
    assert row["total_events"] == 0
    assert row["enforcement_actions"] == 0


def test_counts_are_not_inflated_by_joining_activity_and_enforcement(
    client, admin_headers, db_session, exam, admin_user
):
    """Both counts come from separate subqueries. Joining the rows directly
    would multiply them against each other -- 3 events and 2 enforcement
    actions would report 6 of each."""
    student = _make_student(db_session, "s2", "SE-002", "Busy Candidate", "SE", "D")
    session_row = _make_session(db_session, student, exam, status="in_progress")
    for _ in range(3):
        _add_event(db_session, session_row)

    for _ in range(2):
        client.post(
            "/api/enforcement/actions",
            headers=admin_headers,
            json={
                "session_id": session_row.id,
                "action_type": "UFM_CASE",
                "reason": "Formal referral",
            },
        )

    row = client.get("/api/reports/roster", headers=admin_headers).json()["items"][0]

    assert row["total_events"] == 3
    assert row["enforcement_actions"] == 2


def test_row_reports_activity_by_severity_and_review_status(
    client, admin_headers, db_session, exam
):
    student = _make_student(db_session, "s3", "SE-003", "Mixed Candidate", "SE", "D")
    session_row = _make_session(db_session, student, exam)
    _add_event(db_session, session_row, severity="high", status="CONFIRMED")
    _add_event(db_session, session_row, severity="high", status="PENDING_REVIEW")
    _add_event(db_session, session_row, severity="medium", status="IGNORED")

    row = client.get("/api/reports/roster", headers=admin_headers).json()["items"][0]

    assert row["total_events"] == 3
    assert row["high_severity_events"] == 2
    assert row["confirmed_events"] == 1
    assert row["pending_events"] == 1


# ---------------------------------------------------------------------------
# Cohort filtering
# ---------------------------------------------------------------------------


def test_filter_by_program_and_section(client, admin_headers, db_session, exam):
    se_d = _make_student(db_session, "s4", "SE-004", "Ayesha Khan", "SE", "D")
    se_e = _make_student(db_session, "s5", "SE-005", "Bilal Ahmed", "SE", "E")
    cs_a = _make_student(db_session, "s6", "CS-006", "Hina Malik", "CS", "A")
    for student in (se_d, se_e, cs_a):
        _make_session(db_session, student, exam)

    by_program = client.get(
        "/api/reports/roster", headers=admin_headers, params={"department": "SE"}
    ).json()
    assert by_program["total"] == 2

    by_section = client.get(
        "/api/reports/roster",
        headers=admin_headers,
        params={"department": "SE", "class_name": "D"},
    ).json()
    assert by_section["total"] == 1
    assert by_section["items"][0]["student_full_name"] == "Ayesha Khan"


def test_filter_by_exam_and_session_status(client, admin_headers, db_session, exam):
    other_exam = Exam(title="Physics", duration_minutes=30, status="active")
    db_session.add(other_exam)
    db_session.commit()
    db_session.refresh(other_exam)

    a = _make_student(db_session, "s7", "SE-007", "One", "SE", "D")
    b = _make_student(db_session, "s8", "SE-008", "Two", "SE", "D")
    _make_session(db_session, a, exam, status="submitted")
    _make_session(db_session, b, other_exam, status="cancelled")

    by_exam = client.get(
        "/api/reports/roster", headers=admin_headers, params={"exam_id": exam.id}
    ).json()
    assert by_exam["total"] == 1
    assert by_exam["items"][0]["exam_title"] == "Software Engineering"

    by_status = client.get(
        "/api/reports/roster", headers=admin_headers, params={"session_status": "cancelled"}
    ).json()
    assert by_status["total"] == 1


def test_students_with_no_program_recorded_are_still_listed(
    client, admin_headers, db_session, exam
):
    """Real rosters have incomplete records; those candidates must not
    silently vanish from a cohort report."""
    student = _make_student(db_session, "s9", "X-009", "Unassigned", None, None)
    _make_session(db_session, student, exam)

    body = client.get("/api/reports/roster", headers=admin_headers).json()

    assert body["total"] == 1
    assert body["items"][0]["department"] is None


# ---------------------------------------------------------------------------
# Aggregate totals and provenance
# ---------------------------------------------------------------------------


def test_totals_describe_every_matching_row_not_just_the_page(
    client, admin_headers, db_session, exam
):
    for index in range(4):
        student = _make_student(
            db_session, f"s1{index}", f"SE-1{index}", f"Student {index}", "SE", "D"
        )
        session_row = _make_session(db_session, student, exam)
        if index < 2:
            _add_event(db_session, session_row)

    body = client.get(
        "/api/reports/roster", headers=admin_headers, params={"page_size": 2}
    ).json()

    assert len(body["items"]) == 2
    assert body["total_pages"] == 2
    # Aggregates cover all four sessions, not the two on this page.
    assert body["total_sessions"] == 4
    assert body["sessions_with_activity"] == 2
    assert body["total_flagged_events"] == 2


def test_roster_records_who_generated_it(client, admin_headers):
    body = client.get("/api/reports/roster", headers=admin_headers).json()
    assert body["generated_by"] == "admin1"
    assert body["generated_at"] is not None


def test_filter_options_list_only_values_that_exist(
    client, admin_headers, db_session, exam
):
    _make_student(db_session, "s20", "SE-020", "A", "SE", "D")
    _make_student(db_session, "s21", "CS-021", "B", "CS", "A")
    _make_student(db_session, "s22", "X-022", "C", None, None)

    body = client.get("/api/reports/roster/filters", headers=admin_headers).json()

    assert body["departments"] == ["CS", "SE"]
    assert body["class_names"] == ["A", "D"]
    # NULL is the absence of a value, not a cohort to filter by.
    assert None not in body["departments"]


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


def test_csv_export_returns_a_downloadable_file(client, admin_headers, db_session, exam):
    student = _make_student(db_session, "s30", "SE-030", "Ayesha Khan", "SE", "D")
    session_row = _make_session(db_session, student, exam)
    _add_event(db_session, session_row)

    response = client.get("/api/reports/roster.csv", headers=admin_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert ".csv" in response.headers["content-disposition"]


def test_csv_contains_a_header_and_one_row_per_session(
    client, admin_headers, db_session, exam
):
    for index in range(3):
        student = _make_student(
            db_session, f"s4{index}", f"SE-4{index}", f"Student {index}", "SE", "D"
        )
        _make_session(db_session, student, exam)

    response = client.get("/api/reports/roster.csv", headers=admin_headers)
    rows = list(csv.reader(io.StringIO(response.text)))

    assert rows[0][0] == "Student ID"
    assert rows[0][2] == "Program"
    assert len(rows) == 4  # header plus three sessions


def test_csv_writes_missing_program_as_text_not_a_blank(
    client, admin_headers, db_session, exam
):
    """A blank cell would let a spreadsheet quietly group unrecorded
    programs together with real ones."""
    student = _make_student(db_session, "s50", "X-050", "Unassigned", None, None)
    _make_session(db_session, student, exam)

    response = client.get("/api/reports/roster.csv", headers=admin_headers)
    rows = list(csv.reader(io.StringIO(response.text)))

    assert rows[1][2] == "Not recorded"
    assert rows[1][3] == "Not recorded"


def test_csv_honours_the_same_filters_as_the_json_report(
    client, admin_headers, db_session, exam
):
    _make_session(
        db_session, _make_student(db_session, "s60", "SE-060", "In SE", "SE", "D"), exam
    )
    _make_session(
        db_session, _make_student(db_session, "s61", "CS-061", "In CS", "CS", "A"), exam
    )

    response = client.get(
        "/api/reports/roster.csv", headers=admin_headers, params={"department": "SE"}
    )
    rows = list(csv.reader(io.StringIO(response.text)))

    assert len(rows) == 2
    assert rows[1][1] == "In SE"
