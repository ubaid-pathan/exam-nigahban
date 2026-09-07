"""Tests for structured application logging.

Two things are being protected here.

First, that all seven categories the project requires actually emit
something: authentication, API errors, exam session events, monitoring
events, evidence generation, admin actions and security events. Silence on
success was the original problem, and it stays invisible until someone
needs the record.

Second, that no password, token or key ever reaches a log line. That is the
more damaging of the two to get wrong.
"""

import json
import logging
from datetime import datetime

import pytest

from app.core.logging import EVENT_LOGGER, JsonFormatter, configure_logging, log_event
from app.core.security import hash_password
from app.db.models import Exam, ExamSession, MonitoringEvent, User

STUDENT_PASSWORD = "studentpass123"
ADMIN_PASSWORD = "adminpass123"


class CapturingHandler(logging.Handler):
    """Collects records and their rendered JSON, so tests can assert on
    both the structure and the exact text that would be written."""

    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []
        self.rendered: list[str] = []
        self.setFormatter(JsonFormatter())

    def emit(self, record):
        self.records.append(record)
        self.rendered.append(self.format(record))

    def events(self) -> list[dict]:
        return [json.loads(line) for line in self.rendered]

    def named(self, event: str) -> list[dict]:
        return [item for item in self.events() if item.get("event") == event]

    @property
    def text(self) -> str:
        return "\n".join(self.rendered)


@pytest.fixture
def logs():
    """Captures everything the event logger emits during one test."""
    handler = CapturingHandler()
    logger = logging.getLogger(EVENT_LOGGER)
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ---------------------------------------------------------------------------
# The formatter
# ---------------------------------------------------------------------------


def test_each_record_is_one_json_object(logs):
    log_event("test.event", session_id=7)

    payload = json.loads(logs.rendered[0])
    assert payload["event"] == "test.event"
    assert payload["session_id"] == 7
    assert payload["level"] == "INFO"
    assert payload["ts"]


def test_fields_are_queryable_rather_than_interpolated(logs):
    """The point of structured logging: the value is a field, not a
    substring of a sentence."""
    log_event("exam.session.started", session_id=51, student_id="STU-1001")

    payload = logs.events()[0]
    assert payload["session_id"] == 51
    assert payload["student_id"] == "STU-1001"


def test_a_value_the_formatter_cannot_serialize_does_not_lose_the_event(logs):
    """An unexpected type must not raise inside the logging call and
    discard the record."""
    log_event("test.event", when=datetime(2026, 9, 7, 12, 0, 0))

    payload = logs.events()[0]
    assert "2026-09-07" in payload["when"]


def test_level_can_be_raised_for_security_events(logs):
    log_event("auth.login.failed", level=logging.WARNING, username="someone")
    assert logs.events()[0]["level"] == "WARNING"


def test_configure_logging_is_safe_to_call_repeatedly():
    configure_logging()
    configure_logging("DEBUG")
    assert logging.getLogger().handlers


# ---------------------------------------------------------------------------
# The categories the project requires
# ---------------------------------------------------------------------------


def test_successful_login_is_recorded(client, admin_user, logs):
    _auth_headers(client, "admin1", ADMIN_PASSWORD)

    events = logs.named("auth.login.succeeded")
    assert len(events) == 1
    assert events[0]["username"] == "admin1"
    assert events[0]["role"] == "admin"


def test_failed_login_records_which_account_was_tried(client, admin_user, logs):
    """Without the username there is no way to tell a mistyped password
    from someone working through the admin accounts."""
    client.post("/api/auth/login", json={"username": "admin1", "password": "wrong"})

    events = logs.named("auth.login.failed")
    assert len(events) == 1
    assert events[0]["username"] == "admin1"
    assert events[0]["reason"] == "bad_password"
    assert events[0]["level"] == "WARNING"


def test_login_attempt_on_an_unknown_account_is_distinguished(client, logs):
    client.post("/api/auth/login", json={"username": "ghost", "password": "whatever"})

    assert logs.named("auth.login.failed")[0]["reason"] == "unknown_user"


def test_login_to_a_deactivated_account_is_recorded(client, inactive_user, logs):
    client.post(
        "/api/auth/login", json={"username": "inactive1", "password": "inactivepass123"}
    )

    events = logs.named("auth.login.rejected")
    assert len(events) == 1
    assert events[0]["reason"] == "account_inactive"


def test_logout_is_recorded(client, admin_user, logs):
    headers = _auth_headers(client, "admin1", ADMIN_PASSWORD)
    client.post("/api/auth/logout", headers=headers)

    assert logs.named("auth.logout")[0]["username"] == "admin1"


def test_exam_session_start_and_submit_are_recorded(
    client, admin_user, student_user, student_profile, db_session, logs
):
    exam = Exam(title="CS", duration_minutes=60, status="active")
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)

    headers = _auth_headers(client, "student1", STUDENT_PASSWORD)
    session = client.post(f"/api/student/exams/{exam.id}/start", headers=headers).json()
    client.post(f"/api/student/sessions/{session['id']}/submit", headers=headers)

    started = logs.named("exam.session.started")
    assert started[0]["session_id"] == session["id"]
    assert started[0]["student_id"] == "STU-1001"

    submitted = logs.named("exam.session.submitted")
    assert submitted[0]["session_id"] == session["id"]
    assert "score" in submitted[0]


def test_monitoring_event_and_evidence_are_recorded(
    client, admin_user, student_user, student_profile, db_session, logs
):
    exam = Exam(title="CS", duration_minutes=60, status="active")
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)

    headers = _auth_headers(client, "student1", STUDENT_PASSWORD)
    session = client.post(f"/api/student/exams/{exam.id}/start", headers=headers).json()

    # 1x1 JPEG, enough to pass validation.
    jpeg = (
        "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
        "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA"
        "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q=="
    )
    client.post(
        "/api/monitoring/events",
        headers=headers,
        json={
            "session_id": session["id"],
            "event_type": "FACE_ABSENT",
            "confidence": 0.9,
            "duration_seconds": 6.0,
            "occurrences": 1,
            "severity": "high",
            "evidence_image_base64": jpeg,
        },
    )

    recorded = logs.named("monitoring.event.recorded")
    assert recorded[0]["event_type"] == "FACE_ABSENT"
    assert recorded[0]["severity"] == "high"
    assert recorded[0]["session_id"] == session["id"]

    captured = logs.named("evidence.captured")
    assert captured and captured[0]["size_bytes"] > 0


def test_review_decision_is_recorded(
    client, admin_user, student_user, student_profile, db_session, logs
):
    exam = Exam(title="CS", duration_minutes=60, status="active")
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)
    session_row = ExamSession(
        student_id=student_profile.id,
        exam_id=exam.id,
        started_at=datetime.utcnow(),
        status="in_progress",
    )
    db_session.add(session_row)
    db_session.commit()
    db_session.refresh(session_row)

    from app.db.models import Evidence

    event = MonitoringEvent(
        session_id=session_row.id,
        event_type="FACE_ABSENT",
        confidence=0.9,
        duration_seconds=6.0,
        occurrences=1,
        severity="high",
        status="PENDING_REVIEW",
        detected_at=datetime.utcnow(),
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    evidence = Evidence(
        event_id=event.id,
        image_path="2026/09/07/EVT-1.jpg",
        captured_at=datetime.utcnow(),
        metadata_json={"content_type": "image/jpeg"},
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    headers = _auth_headers(client, "admin1", ADMIN_PASSWORD)
    client.post(
        f"/api/evidence/{evidence.id}/review",
        headers=headers,
        json={"action": "CONFIRMED", "reason": "Face not visible"},
    )

    reviewed = logs.named("evidence.reviewed")
    assert reviewed[0]["decision"] == "CONFIRMED"
    assert reviewed[0]["admin"] == "admin1"


def test_enforcement_action_is_recorded(
    client, admin_user, student_user, student_profile, db_session, logs
):
    exam = Exam(title="CS", duration_minutes=60, status="active")
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)
    session_row = ExamSession(
        student_id=student_profile.id,
        exam_id=exam.id,
        started_at=datetime.utcnow(),
        status="in_progress",
    )
    db_session.add(session_row)
    db_session.commit()
    db_session.refresh(session_row)

    headers = _auth_headers(client, "admin1", ADMIN_PASSWORD)
    client.post(
        "/api/enforcement/actions",
        headers=headers,
        json={
            "session_id": session_row.id,
            "action_type": "BLOCK",
            "reason": "Phone visible in evidence",
            "block_minutes": 5,
        },
    )

    created = logs.named("enforcement.action.created")
    assert created[0]["action_type"] == "BLOCK"
    assert created[0]["admin"] == "admin1"


# ---------------------------------------------------------------------------
# The half of section 20 that matters more
# ---------------------------------------------------------------------------


def test_no_password_reaches_a_log_line_on_a_successful_login(
    client, admin_user, logs
):
    _auth_headers(client, "admin1", ADMIN_PASSWORD)
    assert ADMIN_PASSWORD not in logs.text


def test_no_password_reaches_a_log_line_on_a_failed_login(client, admin_user, logs):
    """The failure path is the tempting one to log verbosely."""
    client.post(
        "/api/auth/login", json={"username": "admin1", "password": "hunter2-secret"}
    )
    assert "hunter2-secret" not in logs.text


def test_no_access_token_reaches_a_log_line(client, admin_user, logs):
    response = client.post(
        "/api/auth/login", json={"username": "admin1", "password": ADMIN_PASSWORD}
    )
    token = response.json()["access_token"]

    client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert token not in logs.text


def test_no_password_hash_reaches_a_log_line(client, admin_user, db_session, logs):
    _auth_headers(client, "admin1", ADMIN_PASSWORD)

    stored_hash = db_session.query(User).filter(User.username == "admin1").first()
    assert stored_hash.password_hash not in logs.text


def test_a_step_up_lockout_records_the_fact_but_never_the_attempt(logs):
    """step_up.py logs that a lockout happened; the password tried must not
    appear anywhere in that record."""
    from app.core.step_up import MAX_FAILED_ATTEMPTS, step_up_verifier

    step_up_verifier.reset()
    handler = CapturingHandler()
    security_logger = logging.getLogger("app.core.step_up")
    security_logger.addHandler(handler)
    try:
        for _ in range(MAX_FAILED_ATTEMPTS):
            step_up_verifier.verify(1, "the-secret-password", hash_password("different"))
    finally:
        security_logger.removeHandler(handler)
        step_up_verifier.reset()

    assert handler.records, "a lockout should be recorded"
    assert "the-secret-password" not in handler.text
