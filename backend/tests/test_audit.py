from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as SQLAlchemySession

from app.db.models import AdminAction, MonitoringEvent


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


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


def _start_session(client, student_headers, exam_id):
    return client.post(
        f"/api/student/exams/{exam_id}/start", headers=student_headers
    ).json()


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


def _create_evidence(client, admin_headers, student_headers, exam_id):
    """Creates an active exam session and a monitoring event (with evidence
    image) for it, returning (event_id, evidence_id)."""
    session = _start_session(client, student_headers, exam_id)
    event = client.post(
        "/api/monitoring/events",
        json=_event_payload(
            session["id"],
            evidence_image_base64=_fake_jpeg_base64(),
        ),
        headers=student_headers,
    ).json()
    return event["id"], event["evidence"]["id"]


def _fake_jpeg_base64() -> str:
    import base64

    return base64.b64encode(b"\xff\xd8\xff" + b"\x00" * 64).decode("ascii")


def _setup_evidence(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    event_id, evidence_id = _create_evidence(client, admin_headers, student_headers, exam["id"])
    return admin_headers, student_headers, event_id, evidence_id


# ---------------------------------------------------------------------------
# Core review behavior
# ---------------------------------------------------------------------------


def test_admin_can_review_evidence_as_confirmed(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    response = client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CONFIRMED"
    assert body["event_id"] == event_id
    assert body["evidence_id"] == evidence_id
    assert body["action"]["action"] == "CONFIRMED"


def test_admin_can_review_evidence_as_ignored(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    response = client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "IGNORED"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "IGNORED"
    assert body["action"]["action"] == "IGNORED"


def test_review_updates_monitoring_event_status(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )

    event = db_session.query(MonitoringEvent).filter(MonitoringEvent.id == event_id).first()
    assert event.status == "CONFIRMED"


def test_admin_action_is_persisted(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )

    actions = db_session.query(AdminAction).filter(AdminAction.event_id == event_id).all()
    assert len(actions) == 1
    assert actions[0].action == "CONFIRMED"


def test_admin_action_stores_authenticated_admin_id(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )

    action = db_session.query(AdminAction).filter(AdminAction.event_id == event_id).first()
    assert action.admin_id == admin_user.id


def test_admin_action_stores_event_id(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )

    action = db_session.query(AdminAction).filter(AdminAction.event_id == event_id).first()
    assert action is not None
    assert action.event_id == event_id


def test_reason_is_stored_when_supplied(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    response = client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "IGNORED", "reason": "False positive after review"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["action"]["reason"] == "False positive after review"

    action = db_session.query(AdminAction).filter(AdminAction.event_id == event_id).first()
    assert action.reason == "False positive after review"


def test_reason_can_be_omitted(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    response = client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["action"]["reason"] is None

    action = db_session.query(AdminAction).filter(AdminAction.event_id == event_id).first()
    assert action.reason is None


# ---------------------------------------------------------------------------
# Validation and authorization
# ---------------------------------------------------------------------------


def test_invalid_action_is_rejected_with_422(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, _, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    response = client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CHEATING_CONFIRMED"},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_nonexistent_evidence_returns_404(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.post(
        "/api/evidence/999999/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_unauthenticated_review_rejected(client):
    response = client.post(
        "/api/evidence/1/review",
        json={"action": "CONFIRMED"},
    )
    assert response.status_code == 401


def test_student_cannot_review_evidence(
    client, admin_user, student_user, student_profile
):
    _, student_headers, _, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    response = client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED"},
        headers=student_headers,
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Repeated review / audit history
# ---------------------------------------------------------------------------


def test_repeated_review_preserves_previous_audit_history(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )
    client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "IGNORED", "reason": "Reconsidered"},
        headers=admin_headers,
    )

    actions = (
        db_session.query(AdminAction)
        .filter(AdminAction.event_id == event_id)
        .order_by(AdminAction.id)
        .all()
    )
    assert len(actions) == 2
    assert actions[0].action == "CONFIRMED"
    assert actions[1].action == "IGNORED"

    event = db_session.query(MonitoringEvent).filter(MonitoringEvent.id == event_id).first()
    assert event.status == "IGNORED"


def test_previous_admin_action_records_are_not_overwritten(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    first = client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED", "reason": "Initial review"},
        headers=admin_headers,
    ).json()
    first_action_id = first["action"]["id"]

    client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )

    original = db_session.query(AdminAction).filter(AdminAction.id == first_action_id).first()
    assert original is not None
    assert original.reason == "Initial review"


# ---------------------------------------------------------------------------
# Transaction safety
# ---------------------------------------------------------------------------


def test_database_failure_does_not_leave_partially_updated_event(
    client, admin_user, student_user, student_profile, db_session, monkeypatch
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    def failing_commit(self):
        raise SQLAlchemyError("simulated database failure")

    monkeypatch.setattr(SQLAlchemySession, "commit", failing_commit)

    response = client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )

    assert response.status_code == 500
    assert "detail" in response.json()

    monkeypatch.undo()

    event = db_session.query(MonitoringEvent).filter(MonitoringEvent.id == event_id).first()
    assert event.status == "PENDING_REVIEW"
    assert db_session.query(AdminAction).filter(AdminAction.event_id == event_id).count() == 0


# ---------------------------------------------------------------------------
# Existing evidence behavior unaffected
# ---------------------------------------------------------------------------


def test_existing_evidence_image_retrieval_unaffected_by_review(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )

    image_response = client.get(f"/api/evidence/{evidence_id}/image", headers=admin_headers)
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/jpeg"


def test_review_response_does_not_leak_filesystem_path(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, event_id, evidence_id = _setup_evidence(
        client, admin_user, student_user, student_profile
    )

    response = client.post(
        f"/api/evidence/{evidence_id}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )

    body = response.json()
    assert "image_path" not in body
    assert "image_path" not in body["action"]
