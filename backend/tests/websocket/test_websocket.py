"""WebSocket infrastructure tests (Phase 7F-1) and monitoring-event
broadcast tests (Phase 7F-2).

Three layers are tested separately:

- ConnectionManager itself, in isolation, using lightweight fake sockets
  (no ASGI/event-loop involved) -- this covers broadcast() and its
  failure-isolation behavior deterministically and fast.
- The real /ws/admin/alerts endpoint, through FastAPI's TestClient, which
  exercises authentication end-to-end (query-param token -> decode ->
  DB lookup -> accept/reject) and the router's use of the shared manager
  singleton.
- POST /api/monitoring/events, through the same real endpoint, verifying
  it broadcasts to a connected admin via that same shared manager without
  changing its own HTTP response or behavior.
"""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.security import create_access_token
from app.websocket.manager import ConnectionManager
from app.websocket.manager import manager as global_manager


# ---------------------------------------------------------------------------
# ConnectionManager unit tests (fake sockets, no network/ASGI layer)
# ---------------------------------------------------------------------------


class _FakeWebSocket:
    def __init__(self, fail_on_send: bool = False) -> None:
        self.accepted = False
        self.sent: list[dict] = []
        self._fail_on_send = fail_on_send

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict) -> None:
        if self._fail_on_send:
            raise RuntimeError("simulated closed socket")
        self.sent.append(message)


def test_manager_can_broadcast_to_connected_admins():
    manager = ConnectionManager()
    admin_a = _FakeWebSocket()
    admin_b = _FakeWebSocket()

    async def scenario():
        await manager.connect(admin_a)
        await manager.connect(admin_b)
        await manager.broadcast({"type": "monitoring_event", "event_id": 1})

    asyncio.run(scenario())

    assert admin_a.accepted is True
    assert admin_b.accepted is True
    assert admin_a.sent == [{"type": "monitoring_event", "event_id": 1}]
    assert admin_b.sent == [{"type": "monitoring_event", "event_id": 1}]


def test_disconnected_client_is_removed():
    manager = ConnectionManager()
    admin_a = _FakeWebSocket()

    asyncio.run(manager.connect(admin_a))
    assert manager.connection_count == 1

    manager.disconnect(admin_a)
    assert manager.connection_count == 0

    # Disconnecting an already-removed (or never-tracked) socket must not
    # raise -- the router calls this unconditionally from a
    # WebSocketDisconnect handler.
    manager.disconnect(admin_a)
    assert manager.connection_count == 0


def test_failed_socket_during_broadcast_does_not_crash_manager():
    manager = ConnectionManager()
    healthy = _FakeWebSocket()
    broken = _FakeWebSocket(fail_on_send=True)

    async def scenario():
        await manager.connect(healthy)
        await manager.connect(broken)
        await manager.broadcast({"type": "monitoring_event", "event_id": 2})

    asyncio.run(scenario())  # must not raise despite `broken` failing

    assert healthy.sent == [{"type": "monitoring_event", "event_id": 2}]
    assert manager.connection_count == 1
    assert broken not in manager._connections


# ---------------------------------------------------------------------------
# /ws/admin/alerts authentication (real endpoint, via TestClient)
# ---------------------------------------------------------------------------


def _login_token(client, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    return response.json()["access_token"]


def _expired_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def test_missing_token_is_rejected(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/admin/alerts"):
            pass


def test_invalid_token_is_rejected(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/admin/alerts?token=not-a-valid-jwt"):
            pass


def test_expired_token_is_rejected(client, admin_user):
    token = _expired_token(admin_user.username, admin_user.role)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/admin/alerts?token={token}"):
            pass


def test_inactive_user_token_is_rejected(client, inactive_user):
    # inactive_user can never log in via /api/auth/login, so its token is
    # minted directly with the existing create_access_token -- this proves
    # the WebSocket layer independently re-checks the account's current
    # status rather than trusting a still-validly-signed token.
    token = create_access_token(inactive_user.username, inactive_user.role)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/admin/alerts?token={token}"):
            pass


def test_student_token_is_rejected(client, admin_user, student_user, student_profile):
    token = _login_token(client, "student1", "studentpass123")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/admin/alerts?token={token}"):
            pass


def test_valid_active_admin_token_is_accepted_and_removed_on_disconnect(
    client, admin_user
):
    token = _login_token(client, "admin1", "adminpass123")
    baseline = global_manager.connection_count

    with client.websocket_connect(f"/ws/admin/alerts?token={token}"):
        assert global_manager.connection_count == baseline + 1

    assert global_manager.connection_count == baseline


# ---------------------------------------------------------------------------
# Monitoring-event broadcast (Phase 7F-2)
# ---------------------------------------------------------------------------


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


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


def _fake_jpeg_base64() -> str:
    return base64.b64encode(b"\xff\xd8\xff" + b"\x00" * 64).decode("ascii")


def _event_payload(session_id, **overrides):
    payload = {
        "session_id": session_id,
        "event_type": "FACE_ABSENT",
        "severity": "high",
        "confidence": 0.9,
        "duration_seconds": 5.5,
        "occurrences": 1,
    }
    payload.update(overrides)
    return payload


def test_monitoring_event_creation_broadcasts_to_connected_admin(
    client, admin_user, student_user, student_profile
):
    # The websocket connection and the HTTP POST both need to run on the
    # same event loop for the broadcast to reach this test's socket (see
    # ConnectionManager.broadcast awaiting websocket.send_json on a
    # connection object bound to whichever loop accepted it) -- entering
    # TestClient's own context manager gives every call made through it a
    # single shared portal/event loop instead of a fresh one per call.
    with client:
        admin_token = _login_token(client, "admin1", "adminpass123")
        admin_headers = _bearer(admin_token)
        student_headers = _bearer(_login_token(client, "student1", "studentpass123"))

        exam = _create_active_exam(client, admin_headers)
        session = _start_session(client, student_headers, exam["id"])

        with client.websocket_connect(f"/ws/admin/alerts?token={admin_token}") as ws:
            response = client.post(
                "/api/monitoring/events",
                json=_event_payload(session["id"]),
                headers=student_headers,
            )
            assert response.status_code == 201
            event = response.json()

            message = ws.receive_json()

    assert message == {
        "type": "monitoring_event",
        "event_id": event["id"],
        "session_id": session["id"],
        "event_type": "FACE_ABSENT",
        "severity": "high",
        "status": "PENDING_REVIEW",
    }


def test_mobile_phone_event_broadcasts_with_event_type_unchanged(
    client, admin_user, student_user, student_profile
):
    """Milestone 6 Phase 2 Step 5: MOBILE_PHONE is a new event_type value,
    not a new code path -- confirms _broadcast_monitoring_event needed no
    changes to carry it through, exactly as designed in the Step 4 report.
    """
    with client:
        admin_token = _login_token(client, "admin1", "adminpass123")
        admin_headers = _bearer(admin_token)
        student_headers = _bearer(_login_token(client, "student1", "studentpass123"))

        exam = _create_active_exam(client, admin_headers)
        session = _start_session(client, student_headers, exam["id"])

        with client.websocket_connect(f"/ws/admin/alerts?token={admin_token}") as ws:
            response = client.post(
                "/api/monitoring/events",
                json=_event_payload(
                    session["id"],
                    event_type="MOBILE_PHONE",
                    severity="high",
                    source="browser_yolox",
                ),
                headers=student_headers,
            )
            assert response.status_code == 201
            event = response.json()

            message = ws.receive_json()

    assert message == {
        "type": "monitoring_event",
        "event_id": event["id"],
        "session_id": session["id"],
        "event_type": "MOBILE_PHONE",
        "severity": "high",
        "status": "PENDING_REVIEW",
    }


def test_broadcast_message_excludes_evidence_and_sensitive_data(
    client, admin_user, student_user, student_profile
):
    with client:
        admin_token = _login_token(client, "admin1", "adminpass123")
        admin_headers = _bearer(admin_token)
        student_headers = _bearer(_login_token(client, "student1", "studentpass123"))

        exam = _create_active_exam(client, admin_headers)
        session = _start_session(client, student_headers, exam["id"])

        with client.websocket_connect(f"/ws/admin/alerts?token={admin_token}") as ws:
            response = client.post(
                "/api/monitoring/events",
                json=_event_payload(
                    session["id"], evidence_image_base64=_fake_jpeg_base64()
                ),
                headers=student_headers,
            )
            assert response.status_code == 201
            # Evidence WAS attached on the HTTP side -- proving its absence
            # from the broadcast below is a deliberate omission, not an
            # accident of this particular request having no evidence.
            assert response.json()["evidence"] is not None

            message = ws.receive_json()

    assert set(message.keys()) == {
        "type",
        "event_id",
        "session_id",
        "event_type",
        "severity",
        "status",
    }


def test_monitoring_event_creation_succeeds_without_connected_websocket_clients(
    client, admin_user, student_user, student_profile
):
    admin_headers = _bearer(_login_token(client, "admin1", "adminpass123"))
    student_headers = _bearer(_login_token(client, "student1", "studentpass123"))
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])

    assert global_manager.connection_count == 0

    response = client.post(
        "/api/monitoring/events",
        json=_event_payload(session["id"]),
        headers=student_headers,
    )

    assert response.status_code == 201
    assert response.json()["event_type"] == "FACE_ABSENT"


def test_monitoring_event_creation_succeeds_when_broadcast_raises(
    client, admin_user, student_user, student_profile, monkeypatch
):
    from app.api.routes import monitoring as monitoring_module

    async def _raise(*_args, **_kwargs):
        raise RuntimeError("simulated broadcast failure")

    monkeypatch.setattr(monitoring_module.websocket_manager, "broadcast", _raise)

    admin_headers = _bearer(_login_token(client, "admin1", "adminpass123"))
    student_headers = _bearer(_login_token(client, "student1", "studentpass123"))
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])

    response = client.post(
        "/api/monitoring/events",
        json=_event_payload(session["id"]),
        headers=student_headers,
    )

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING_REVIEW"


# ---------------------------------------------------------------------------
# Existing behavior unaffected
# ---------------------------------------------------------------------------


def test_health_endpoint_still_works(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_existing_http_login_unaffected(client, admin_user):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin1", "password": "adminpass123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
