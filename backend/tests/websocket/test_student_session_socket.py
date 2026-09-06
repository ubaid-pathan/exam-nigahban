"""Tests for the student's live exam-session channel.

The channel exists so an invigilator's pause or cancellation reaches the
candidate at once rather than on their next poll. Two properties matter
most here and are asserted directly:

  * a student may only watch THEIR OWN session -- otherwise any candidate
    could learn when a classmate is paused or cancelled;
  * the frame carries no enforcement state, only a nudge, so it can never
    place a client into a state the API did not authorise.
"""

import asyncio
from datetime import datetime

import pytest
from fastapi import WebSocketDisconnect

from app.core.security import hash_password
from app.db.models import Exam, ExamSession, Student, User
from app.websocket.session_manager import SessionConnectionManager


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _token(client, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    return response.json()["access_token"]


@pytest.fixture
def exam(db_session):
    row = Exam(title="CS", duration_minutes=60, status="active")
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
def other_student_session(db_session, exam):
    user = User(
        username="student_other",
        password_hash=hash_password("otherpass123"),
        role="student",
        status=True,
    )
    db_session.add(user)
    db_session.flush()
    student = Student(
        user_id=user.id, student_id="STU-9002", full_name="Other Student", is_active=True
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    row = ExamSession(
        student_id=student.id,
        exam_id=exam.id,
        started_at=datetime.utcnow(),
        status="in_progress",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Authentication and ownership
# ---------------------------------------------------------------------------


def test_connection_without_a_token_is_rejected(client, session_row):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/student/sessions/{session_row.id}"):
            pass


def test_connection_with_an_invalid_token_is_rejected(client, session_row):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/ws/student/sessions/{session_row.id}?token=not-a-jwt"
        ):
            pass


def test_admin_cannot_use_the_student_channel(
    client, admin_user, student_profile, session_row
):
    token = _token(client, "admin1", "adminpass123")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/ws/student/sessions/{session_row.id}?token={token}"
        ):
            pass


def test_student_can_connect_to_their_own_session(
    client, student_user, student_profile, session_row
):
    token = _token(client, "student1", "studentpass123")
    with client.websocket_connect(
        f"/ws/student/sessions/{session_row.id}?token={token}"
    ) as ws:
        assert ws is not None


def test_student_cannot_watch_another_candidates_session(
    client, student_user, student_profile, other_student_session
):
    """The property that stops a candidate learning when a classmate is
    paused or cancelled."""
    token = _token(client, "student1", "studentpass123")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/ws/student/sessions/{other_student_session.id}?token={token}"
        ):
            pass


def test_unknown_session_is_rejected(client, student_user, student_profile):
    token = _token(client, "student1", "studentpass123")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/student/sessions/999999?token={token}"):
            pass


def test_deactivated_student_cannot_connect(
    client, student_user, student_profile, session_row, db_session
):
    token = _token(client, "student1", "studentpass123")
    student_user.status = False
    db_session.add(student_user)
    db_session.commit()

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/ws/student/sessions/{session_row.id}?token={token}"
        ):
            pass


# ---------------------------------------------------------------------------
# Delivery: enforcement reaches the candidate immediately
# ---------------------------------------------------------------------------


def test_block_nudges_the_connected_student(
    client, admin_user, student_user, student_profile, session_row
):
    student_token = _token(client, "student1", "studentpass123")
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    with client.websocket_connect(
        f"/ws/student/sessions/{session_row.id}?token={student_token}"
    ) as ws:
        response = client.post(
            "/api/enforcement/actions",
            headers=admin_headers,
            json={
                "session_id": session_row.id,
                "action_type": "BLOCK",
                "reason": "Phone visible in evidence",
                "block_minutes": 5,
            },
        )
        assert response.status_code == 201

        message = ws.receive_json()
        assert message["type"] == "session_updated"
        assert message["session_id"] == session_row.id
        # The nudge must carry NO enforcement detail: the client re-reads
        # the session and applies only what the API authorises.
        assert set(message) == {"type", "session_id"}
        assert "blocked_until" not in message
        assert "reason" not in message


def test_cancel_nudges_the_connected_student(
    client, admin_user, student_user, student_profile, session_row
):
    student_token = _token(client, "student1", "studentpass123")
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    with client.websocket_connect(
        f"/ws/student/sessions/{session_row.id}?token={student_token}"
    ) as ws:
        response = client.post(
            "/api/enforcement/actions",
            headers=admin_headers,
            json={
                "session_id": session_row.id,
                "action_type": "CANCEL_EXAM",
                "reason": "Repeated confirmed violations",
            },
        )
        assert response.status_code == 201
        assert ws.receive_json()["session_id"] == session_row.id


def test_lifting_a_block_nudges_the_connected_student(
    client, admin_user, student_user, student_profile, session_row
):
    student_token = _token(client, "student1", "studentpass123")
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    created = client.post(
        "/api/enforcement/actions",
        headers=admin_headers,
        json={
            "session_id": session_row.id,
            "action_type": "BLOCK",
            "reason": "Looking away repeatedly",
            "block_minutes": 5,
        },
    ).json()

    with client.websocket_connect(
        f"/ws/student/sessions/{session_row.id}?token={student_token}"
    ) as ws:
        response = client.post(
            f"/api/enforcement/actions/{created['id']}/lift", headers=admin_headers
        )
        assert response.status_code == 200
        assert ws.receive_json()["type"] == "session_updated"


def test_enforcement_succeeds_with_no_student_connected(
    client, admin_user, student_user, student_profile, session_row
):
    """Nobody watching must never fail the admin's action -- the student's
    polling fallback still delivers it."""
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    response = client.post(
        "/api/enforcement/actions",
        headers=admin_headers,
        json={
            "session_id": session_row.id,
            "action_type": "BLOCK",
            "reason": "No socket attached",
            "block_minutes": 5,
        },
    )
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------


# Driven with asyncio.run rather than @pytest.mark.asyncio, matching
# tests/websocket/test_websocket.py -- this project has no pytest-asyncio
# dependency and does not need one for these.


def test_manager_drops_empty_sessions() -> None:
    """The session map must not grow without bound across many exams."""
    manager = SessionConnectionManager()

    class FakeSocket:
        async def accept(self):
            return None

        async def send_json(self, message):
            return None

    socket = FakeSocket()

    async def scenario():
        await manager.connect(41, socket)
        assert manager.connection_count(41) == 1

        manager.disconnect(41, socket)
        assert manager.connection_count(41) == 0
        assert 41 not in manager._by_session

    asyncio.run(scenario())


def test_manager_only_notifies_the_target_session() -> None:
    manager = SessionConnectionManager()
    received: dict[int, list] = {41: [], 42: []}

    class FakeSocket:
        def __init__(self, key):
            self.key = key

        async def accept(self):
            return None

        async def send_json(self, message):
            received[self.key].append(message)

    async def scenario():
        await manager.connect(41, FakeSocket(41))
        await manager.connect(42, FakeSocket(42))
        await manager.notify_session(41)

    asyncio.run(scenario())

    assert len(received[41]) == 1
    assert received[42] == []


def test_manager_drops_a_failing_socket_without_aborting_delivery() -> None:
    manager = SessionConnectionManager()
    delivered = []

    class BrokenSocket:
        async def accept(self):
            return None

        async def send_json(self, message):
            raise RuntimeError("connection gone")

    class GoodSocket:
        async def accept(self):
            return None

        async def send_json(self, message):
            delivered.append(message)

    async def scenario():
        await manager.connect(41, BrokenSocket())
        await manager.connect(41, GoodSocket())
        await manager.notify_session(41)

    asyncio.run(scenario())

    assert len(delivered) == 1
    assert manager.connection_count(41) == 1
