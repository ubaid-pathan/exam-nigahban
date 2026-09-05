from datetime import datetime, timedelta

from app.core.security import hash_password
from app.db.models import MonitoringEvent, Student, User


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_second_student(db_session):
    user = User(
        username="student2",
        password_hash=hash_password("studentpass456"),
        role="student",
        status=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    student = Student(
        user_id=user.id,
        student_id="STU-2002",
        full_name="Second Student",
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return user, student


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


def _event_payload(session_id, **overrides):
    payload = {
        "session_id": session_id,
        "event_type": "HEAD_LEFT",
        "severity": "medium",
        "confidence": 0.87,
        "duration_seconds": 4.2,
        "occurrences": 3,
    }
    payload.update(overrides)
    return payload


def _fake_jpeg_base64() -> str:
    import base64

    return base64.b64encode(b"\xff\xd8\xff" + b"\x00" * 64).decode("ascii")


def _create_event(client, student_headers, session_id, with_evidence=False, **overrides):
    payload = _event_payload(session_id, **overrides)
    if with_evidence:
        payload["evidence_image_base64"] = _fake_jpeg_base64()
    return client.post(
        "/api/monitoring/events",
        json=payload,
        headers=student_headers,
    ).json()


def _bootstrap_single_event(client, admin_user, student_user, student_profile, **overrides):
    """Creates one active exam + student session + monitoring event.

    Returns (admin_headers, student_headers, exam, session, event).
    """
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])
    event = _create_event(client, student_headers, session["id"], **overrides)
    return admin_headers, student_headers, exam, session, event


# ---------------------------------------------------------------------------
# Core listing / authorization
# ---------------------------------------------------------------------------


def test_admin_can_list_monitoring_events(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, exam, session, event = _bootstrap_single_event(
        client, admin_user, student_user, student_profile, with_evidence=True
    )

    response = client.get("/api/monitoring/events", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == event["id"]
    assert item["session_id"] == session["id"]
    assert item["event_type"] == "HEAD_LEFT"
    assert item["status"] == "PENDING_REVIEW"
    assert item["exam_id"] == exam["id"]
    assert item["exam_title"] == exam["title"]
    assert item["student_id"] == "STU-1001"
    assert item["student_full_name"] == "Test Student"
    assert item["evidence_id"] == event["evidence"]["id"]


def test_unauthenticated_request_returns_401(client):
    response = client.get("/api/monitoring/events")
    assert response.status_code == 401


def test_student_request_returns_403(client, admin_user, student_user, student_profile):
    _, student_headers, _, _, _ = _bootstrap_single_event(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/monitoring/events", headers=student_headers)
    assert response.status_code == 403


def test_empty_result_when_no_events(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.get("/api/monitoring/events", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["total_pages"] == 0


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_status_filter(client, admin_user, student_user, student_profile):
    admin_headers, _, _, _, event = _bootstrap_single_event(
        client, admin_user, student_user, student_profile
    )

    matching = client.get(
        "/api/monitoring/events?status=PENDING_REVIEW", headers=admin_headers
    )
    assert matching.status_code == 200
    assert len(matching.json()["items"]) == 1

    non_matching = client.get(
        "/api/monitoring/events?status=CONFIRMED", headers=admin_headers
    )
    assert non_matching.status_code == 200
    assert non_matching.json()["items"] == []


def test_severity_filter(client, admin_user, student_user, student_profile):
    # FACE_ABSENT is configured as severity "high"; HEAD_LEFT is "medium".
    admin_headers, student_headers, exam, session, _ = _bootstrap_single_event(
        client,
        admin_user,
        student_user,
        student_profile,
        event_type="FACE_ABSENT",
        severity="high",
        duration_seconds=5.0,
    )

    matching = client.get(
        "/api/monitoring/events?severity=high", headers=admin_headers
    )
    assert len(matching.json()["items"]) == 1

    non_matching = client.get(
        "/api/monitoring/events?severity=low", headers=admin_headers
    )
    assert non_matching.json()["items"] == []


def test_event_type_filter(client, admin_user, student_user, student_profile):
    admin_headers, _, _, _, _ = _bootstrap_single_event(
        client,
        admin_user,
        student_user,
        student_profile,
        event_type="FACE_ABSENT",
        severity="high",
        duration_seconds=5.0,
    )

    matching = client.get(
        "/api/monitoring/events?event_type=FACE_ABSENT", headers=admin_headers
    )
    assert len(matching.json()["items"]) == 1

    non_matching = client.get(
        "/api/monitoring/events?event_type=HEAD_RIGHT", headers=admin_headers
    )
    assert non_matching.json()["items"] == []


def test_session_id_filter(client, admin_user, student_user, student_profile, db_session):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session_a = _start_session(client, student_headers, exam["id"])
    event_a = _create_event(client, student_headers, session_a["id"])

    _make_second_student(db_session)
    other_headers = _auth_headers(client, "student2", "studentpass456")
    session_b = _start_session(client, other_headers, exam["id"])
    event_b = _create_event(client, other_headers, session_b["id"])

    response = client.get(
        f"/api/monitoring/events?session_id={session_a['id']}", headers=admin_headers
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == event_a["id"]
    assert items[0]["session_id"] == session_a["id"]


def test_combined_filters(client, admin_user, student_user, student_profile):
    admin_headers, student_headers, exam, session, _ = _bootstrap_single_event(
        client,
        admin_user,
        student_user,
        student_profile,
        event_type="FACE_ABSENT",
        severity="high",
        duration_seconds=5.0,
    )
    # A second, non-matching event in the same session.
    _create_event(
        client,
        student_headers,
        session["id"],
        event_type="HEAD_LEFT",
        severity="medium",
    )

    response = client.get(
        "/api/monitoring/events"
        f"?session_id={session['id']}&event_type=FACE_ABSENT&severity=high&status=PENDING_REVIEW",
        headers=admin_headers,
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["event_type"] == "FACE_ABSENT"
    assert items[0]["severity"] == "high"


# ---------------------------------------------------------------------------
# Pagination and ordering
# ---------------------------------------------------------------------------


def test_pagination(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])

    for _ in range(3):
        _create_event(client, student_headers, session["id"])

    page_1 = client.get(
        "/api/monitoring/events?page=1&page_size=2", headers=admin_headers
    ).json()
    assert len(page_1["items"]) == 2
    assert page_1["total"] == 3
    assert page_1["total_pages"] == 2
    assert page_1["page"] == 1
    assert page_1["page_size"] == 2

    page_2 = client.get(
        "/api/monitoring/events?page=2&page_size=2", headers=admin_headers
    ).json()
    assert len(page_2["items"]) == 1
    assert page_2["page"] == 2

    ids_page_1 = {item["id"] for item in page_1["items"]}
    ids_page_2 = {item["id"] for item in page_2["items"]}
    assert ids_page_1.isdisjoint(ids_page_2)


def test_deterministic_ordering_newest_first(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])

    first = _create_event(client, student_headers, session["id"])
    second = _create_event(client, student_headers, session["id"])
    third = _create_event(client, student_headers, session["id"])

    # Force identical detected_at timestamps to prove ordering stays
    # deterministic (via the id DESC tiebreaker) even without timestamp
    # separation between events.
    same_time = datetime(2026, 1, 1, 12, 0, 0)
    for event_id in (first["id"], second["id"], third["id"]):
        row = db_session.get(MonitoringEvent, event_id)
        row.detected_at = same_time
    db_session.commit()

    response = client.get("/api/monitoring/events", headers=admin_headers)
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [third["id"], second["id"], first["id"]]

    # Ordering must be stable across repeated requests.
    response_again = client.get("/api/monitoring/events", headers=admin_headers)
    ids_again = [item["id"] for item in response_again.json()["items"]]
    assert ids_again == ids


def test_invalid_pagination_parameters_return_422(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    assert client.get(
        "/api/monitoring/events?page=0", headers=admin_headers
    ).status_code == 422
    assert client.get(
        "/api/monitoring/events?page=-1", headers=admin_headers
    ).status_code == 422
    assert client.get(
        "/api/monitoring/events?page_size=0", headers=admin_headers
    ).status_code == 422
    assert client.get(
        "/api/monitoring/events?page_size=101", headers=admin_headers
    ).status_code == 422


# ---------------------------------------------------------------------------
# Data shape / security
# ---------------------------------------------------------------------------


def test_evidence_id_returned_when_evidence_exists(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, _, _, event = _bootstrap_single_event(
        client, admin_user, student_user, student_profile, with_evidence=True
    )

    response = client.get("/api/monitoring/events", headers=admin_headers)
    item = response.json()["items"][0]
    assert item["evidence_id"] == event["evidence"]["id"]


def test_evidence_id_is_none_when_no_evidence(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, _, _, _ = _bootstrap_single_event(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/monitoring/events", headers=admin_headers)
    item = response.json()["items"][0]
    assert item["evidence_id"] is None


def test_image_path_never_exposed(client, admin_user, student_user, student_profile):
    admin_headers, _, _, _, _ = _bootstrap_single_event(
        client, admin_user, student_user, student_profile, with_evidence=True
    )

    response = client.get("/api/monitoring/events", headers=admin_headers)
    body = response.json()
    assert "image_path" not in body
    for item in body["items"]:
        assert "image_path" not in item


def test_password_hash_never_exposed(client, admin_user, student_user, student_profile):
    admin_headers, _, _, _, _ = _bootstrap_single_event(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/monitoring/events", headers=admin_headers)
    body = response.json()
    assert "password_hash" not in body
    for item in body["items"]:
        assert "password_hash" not in item


def test_student_and_exam_context_returned_correctly(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, exam, session, event = _bootstrap_single_event(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/monitoring/events", headers=admin_headers)
    item = response.json()["items"][0]

    assert item["student_id"] == student_profile.student_id
    assert item["student_full_name"] == student_profile.full_name
    assert item["exam_id"] == exam["id"]
    assert item["exam_title"] == exam["title"]


# ---------------------------------------------------------------------------
# Interop with Phase 7A review
# ---------------------------------------------------------------------------


def test_reviewed_and_pending_events_both_retrievable(
    client, admin_user, student_user, student_profile
):
    admin_headers, student_headers, exam, session, event = _bootstrap_single_event(
        client, admin_user, student_user, student_profile, with_evidence=True
    )
    pending_event = _create_event(client, student_headers, session["id"])

    client.post(
        f"/api/evidence/{event['evidence']['id']}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )

    response = client.get("/api/monitoring/events", headers=admin_headers)
    body = response.json()
    assert body["total"] == 2
    statuses = {item["id"]: item["status"] for item in body["items"]}
    assert statuses[event["id"]] == "CONFIRMED"
    assert statuses[pending_event["id"]] == "PENDING_REVIEW"

    confirmed_only = client.get(
        "/api/monitoring/events?status=CONFIRMED", headers=admin_headers
    ).json()
    assert len(confirmed_only["items"]) == 1
    assert confirmed_only["items"][0]["id"] == event["id"]


def test_existing_evidence_review_functionality_still_works(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, _, _, event = _bootstrap_single_event(
        client, admin_user, student_user, student_profile, with_evidence=True
    )

    response = client.post(
        f"/api/evidence/{event['evidence']['id']}/review",
        json={"action": "IGNORED", "reason": "False positive"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "IGNORED"
    assert body["action"]["reason"] == "False positive"


# ---------------------------------------------------------------------------
# MOBILE_PHONE (Milestone 6 Phase 2 Step 5 -- YOLOX Worker pipeline)
# ---------------------------------------------------------------------------


def test_mobile_phone_event_appears_in_admin_listing(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, _, session, event = _bootstrap_single_event(
        client,
        admin_user,
        student_user,
        student_profile,
        event_type="MOBILE_PHONE",
        severity="high",
    )

    response = client.get("/api/monitoring/events", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == event["id"]
    assert item["session_id"] == session["id"]
    assert item["event_type"] == "MOBILE_PHONE"
    assert item["severity"] == "high"


def test_mobile_phone_event_type_filter(client, admin_user, student_user, student_profile):
    _bootstrap_single_event(
        client,
        admin_user,
        student_user,
        student_profile,
        event_type="MOBILE_PHONE",
        severity="high",
    )
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    matching = client.get(
        "/api/monitoring/events?event_type=MOBILE_PHONE", headers=admin_headers
    )
    assert len(matching.json()["items"]) == 1
    assert matching.json()["items"][0]["event_type"] == "MOBILE_PHONE"

    non_matching = client.get(
        "/api/monitoring/events?event_type=HEAD_RIGHT", headers=admin_headers
    )
    assert non_matching.json()["items"] == []
