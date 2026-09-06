"""S3-backed evidence storage behavior.

The boto3 client is replaced with a MagicMock via the service module's
client cache, so no network or real object storage is needed. What is
verified here is the contract the rest of the application depends on:

* save uploads via put_object with a forward-slash key and JPEG type
* read returns object bytes; a missing object raises FileNotFoundError
  (an OSError) so the route-level base64 fallback keeps working
* delete is best-effort and never raises
* events created while the durable backend is active do NOT embed the
  base64 fallback copy in the DB metadata (no row bloat)
* the local backend keeps embedding the base64 fallback as before
"""

import base64
import io
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.core.config import settings
from app.db.models import Evidence
from app.services import evidence_storage

TEST_BUCKET = "test-evidence-bucket"


def _client_error(code: str, operation: str = "GetObject") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "boom"}}, operation)


@pytest.fixture
def s3_backend(monkeypatch):
    """Activates the s3 backend with a mocked boto3 client."""
    mock_client = MagicMock()
    monkeypatch.setattr(settings, "evidence_backend", "s3")
    monkeypatch.setattr(settings, "evidence_s3_bucket", TEST_BUCKET)
    monkeypatch.setattr(evidence_storage, "_s3_client_cache", mock_client)
    yield mock_client


# ---------------------------------------------------------------------------
# Unit-level storage contract
# ---------------------------------------------------------------------------


def test_evidence_storage_is_durable_reflects_backend(monkeypatch):
    assert evidence_storage.evidence_storage_is_durable() is False
    monkeypatch.setattr(settings, "evidence_backend", "s3")
    assert evidence_storage.evidence_storage_is_durable() is True


def test_save_evidence_image_uploads_object(s3_backend):
    key = evidence_storage.save_evidence_image(
        b"\xff\xd8\xffrest", 42, datetime(2026, 9, 5, 12, 30)
    )
    # Forward-slash key (S3-safe and platform-independent), same
    # YYYY/MM/DD/EVT-<id>.jpg layout as the local backend.
    assert key == "2026/09/05/EVT-000042.jpg"
    s3_backend.put_object.assert_called_once_with(
        Bucket=TEST_BUCKET,
        Key="2026/09/05/EVT-000042.jpg",
        Body=b"\xff\xd8\xffrest",
        ContentType="image/jpeg",
    )


def test_upload_evidence_object_uses_explicit_key(s3_backend):
    evidence_storage.upload_evidence_object(
        b"\xff\xd8\xfflegacy", "2026/08/23/EVT-000007.jpg"
    )
    s3_backend.put_object.assert_called_once_with(
        Bucket=TEST_BUCKET,
        Key="2026/08/23/EVT-000007.jpg",
        Body=b"\xff\xd8\xfflegacy",
        ContentType="image/jpeg",
    )


def test_save_failure_raises_oserror(s3_backend):
    s3_backend.put_object.side_effect = _client_error("AccessDenied", "PutObject")
    with pytest.raises(OSError):
        evidence_storage.save_evidence_image(
            b"\xff\xd8\xff", 42, datetime(2026, 9, 5)
        )


def test_read_evidence_image_returns_object_bytes(s3_backend):
    s3_backend.get_object.return_value = {"Body": io.BytesIO(b"\xff\xd8\xffbytes")}
    result = evidence_storage.read_evidence_image("2026/09/05/EVT-000042.jpg")
    assert result == b"\xff\xd8\xffbytes"
    s3_backend.get_object.assert_called_once_with(
        Bucket=TEST_BUCKET,
        Key="2026/09/05/EVT-000042.jpg",
    )


def test_read_missing_object_raises_file_not_found_error(s3_backend):
    s3_backend.get_object.side_effect = _client_error("NoSuchKey")
    with pytest.raises(FileNotFoundError):
        evidence_storage.read_evidence_image("gone.jpg")


def test_read_missing_object_still_caught_by_route_fallback(s3_backend):
    # The evidence route catches OSError to trigger its base64 fallback,
    # so a missing S3 object must remain an OSError.
    s3_backend.get_object.side_effect = _client_error("404")
    with pytest.raises(OSError):
        evidence_storage.read_evidence_image("gone.jpg")


def test_read_transport_failure_raises_oserror(s3_backend):
    s3_backend.get_object.side_effect = _client_error("AccessDenied")
    with pytest.raises(OSError):
        evidence_storage.read_evidence_image("x.jpg")


def test_delete_evidence_file_is_best_effort(s3_backend):
    s3_backend.delete_object.side_effect = _client_error(
        "AccessDenied", "DeleteObject"
    )
    evidence_storage.delete_evidence_file("2026/09/05/EVT-000042.jpg")
    s3_backend.delete_object.assert_called_once_with(
        Bucket=TEST_BUCKET,
        Key="2026/09/05/EVT-000042.jpg",
    )


# ---------------------------------------------------------------------------
# API-level behavior (metadata fallback policy)
# ---------------------------------------------------------------------------


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


def _create_event_with_evidence(client, admin_headers, student_headers):
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])
    response = client.post(
        "/api/monitoring/events",
        json=_event_payload(session["id"], evidence_image_base64=_FAKE_JPEG_BASE64),
        headers=student_headers,
    )
    assert response.status_code == 201
    return response.json()


def test_durable_backend_omits_base64_fallback(
    client, admin_user, student_user, student_profile, db_session, s3_backend
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")

    body = _create_event_with_evidence(client, admin_headers, student_headers)

    assert body["evidence"] is not None
    assert body["evidence"]["metadata"]["content_type"] == "image/jpeg"
    assert body["evidence"]["metadata"]["size_bytes"] == len(_FAKE_JPEG_BYTES)
    assert "image_base64" not in body["evidence"]["metadata"]
    s3_backend.put_object.assert_called_once()

    row = (
        db_session.query(Evidence)
        .filter(Evidence.event_id == body["id"])
        .first()
    )
    assert row is not None
    assert "image_base64" not in row.metadata_json
    # Stored path is a forward-slash object key, never a Windows path.
    assert "/" in row.image_path
    assert "\\" not in row.image_path
    assert f"EVT-{body['id']:06d}.jpg" in row.image_path


def test_durable_backend_image_served_from_object_storage(
    client, admin_user, student_user, student_profile, s3_backend
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")

    body = _create_event_with_evidence(client, admin_headers, student_headers)
    s3_backend.get_object.return_value = {"Body": io.BytesIO(_FAKE_JPEG_BYTES)}

    image_response = client.get(
        f"/api/evidence/{body['evidence']['id']}/image", headers=admin_headers
    )
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/jpeg"
    assert image_response.content == _FAKE_JPEG_BYTES


def test_durable_backend_missing_object_returns_404(
    client, admin_user, student_user, student_profile, s3_backend
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")

    body = _create_event_with_evidence(client, admin_headers, student_headers)
    s3_backend.get_object.side_effect = _client_error("NoSuchKey")

    image_response = client.get(
        f"/api/evidence/{body['evidence']['id']}/image", headers=admin_headers
    )
    # With no DB fallback copy kept, a genuinely missing object is a 404.
    assert image_response.status_code == 404


def test_local_backend_keeps_base64_fallback(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")

    body = _create_event_with_evidence(client, admin_headers, student_headers)

    row = (
        db_session.query(Evidence)
        .filter(Evidence.event_id == body["id"])
        .first()
    )
    assert row is not None
    # Ephemeral filesystem: the DB row still carries the survival copy.
    assert row.metadata_json.get("image_base64") == _FAKE_JPEG_BASE64
