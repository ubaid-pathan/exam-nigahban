import base64

from app.db.models import Evidence, MonitoringEvent


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


# A minimal payload satisfying the JPEG magic-byte check (FF D8 FF) plus
# harmless padding -- the storage layer intentionally only validates magic
# bytes/size, not full JPEG structure (no image-parsing dependency).
_FAKE_JPEG_BYTES = b"\xff\xd8\xff" + b"\x00" * 128
_FAKE_JPEG_BASE64 = base64.b64encode(_FAKE_JPEG_BYTES).decode("ascii")


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


# ---------------------------------------------------------------------------


def test_event_with_valid_evidence_image_creates_evidence(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = _start_session(client, student_headers, exam["id"])

    response = client.post(
        "/api/monitoring/events",
        json=_event_payload(session["id"], evidence_image_base64=_FAKE_JPEG_BASE64),
        headers=student_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["evidence"] is not None
    assert body["evidence"]["event_id"] == body["id"]
    assert body["evidence"]["metadata"]["content_type"] == "image/jpeg"
    assert body["evidence"]["metadata"]["size_bytes"] == len(_FAKE_JPEG_BYTES)
    # Raw filesystem path must never be exposed via the API.
    assert "image_path" not in body["evidence"]


def test_event_without_image_has_no_evidence(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = _start_session(client, student_headers, exam["id"])

    response = client.post(
        "/api/monitoring/events",
        json=_event_payload(session["id"]),
        headers=student_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["evidence"] is None
    assert db_session.query(Evidence).filter(Evidence.event_id == body["id"]).first() is None


def test_invalid_base64_evidence_does_not_break_event_creation(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = _start_session(client, student_headers, exam["id"])

    response = client.post(
        "/api/monitoring/events",
        json=_event_payload(session["id"], evidence_image_base64="not-valid-base64!!!"),
        headers=student_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["evidence"] is None
    assert db_session.query(MonitoringEvent).filter(MonitoringEvent.id == body["id"]).first() is not None


def test_oversized_evidence_does_not_break_event_creation(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = _start_session(client, student_headers, exam["id"])

    oversized = base64.b64encode(b"\xff\xd8\xff" + b"\x00" * 400_000).decode("ascii")
    response = client.post(
        "/api/monitoring/events",
        json=_event_payload(session["id"], evidence_image_base64=oversized),
        headers=student_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["evidence"] is None
    assert db_session.query(Evidence).filter(Evidence.event_id == body["id"]).first() is None


def test_non_jpeg_evidence_does_not_break_event_creation(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = _start_session(client, student_headers, exam["id"])

    not_a_jpeg = base64.b64encode(b"this is plain text, not a jpeg").decode("ascii")
    response = client.post(
        "/api/monitoring/events",
        json=_event_payload(session["id"], evidence_image_base64=not_a_jpeg),
        headers=student_headers,
    )
    assert response.status_code == 201
    assert response.json()["evidence"] is None


def test_admin_retrieves_evidence_image(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = _start_session(client, student_headers, exam["id"])

    event = client.post(
        "/api/monitoring/events",
        json=_event_payload(session["id"], evidence_image_base64=_FAKE_JPEG_BASE64),
        headers=student_headers,
    ).json()
    evidence_id = event["evidence"]["id"]

    image_response = client.get(f"/api/evidence/{evidence_id}/image", headers=admin_headers)
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/jpeg"
    assert image_response.content == _FAKE_JPEG_BYTES


def test_admin_lists_and_filters_evidence(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    exam = _create_active_exam(client, admin_headers)
    student_headers = _auth_headers(client, "student1", "studentpass123")
    session = _start_session(client, student_headers, exam["id"])

    event = client.post(
        "/api/monitoring/events",
        json=_event_payload(session["id"], evidence_image_base64=_FAKE_JPEG_BASE64),
        headers=student_headers,
    ).json()

    list_response = client.get("/api/evidence", headers=admin_headers)
    assert list_response.status_code == 200
    assert any(e["event_id"] == event["id"] for e in list_response.json())

    filtered = client.get(
        f"/api/evidence?session_id={session['id']}", headers=admin_headers
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    detail = client.get(f"/api/evidence/{event['evidence']['id']}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["event_id"] == event["id"]


def test_student_cannot_access_evidence_endpoints(
    client, admin_user, student_user, student_profile
):
    student_headers = _auth_headers(client, "student1", "studentpass123")
    assert client.get("/api/evidence", headers=student_headers).status_code == 403
    assert client.get("/api/evidence/1", headers=student_headers).status_code == 403
    assert client.get("/api/evidence/1/image", headers=student_headers).status_code == 403


def test_unauthenticated_evidence_access_rejected(client):
    assert client.get("/api/evidence").status_code == 401
    assert client.get("/api/evidence/1").status_code == 401
    assert client.get("/api/evidence/1/image").status_code == 401


def test_evidence_not_found_returns_404(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    assert client.get("/api/evidence/999999", headers=admin_headers).status_code == 404
    assert client.get("/api/evidence/999999/image", headers=admin_headers).status_code == 404
