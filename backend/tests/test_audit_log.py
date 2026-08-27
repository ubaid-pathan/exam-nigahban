from datetime import datetime

from app.db.models import AdminAction


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = response.json()["access_token"]
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
    import base64

    return base64.b64encode(b"\xff\xd8\xff" + b"\x00" * 64).decode("ascii")


def _event_payload(session_id, **overrides):
    payload = {
        "session_id": session_id,
        "event_type": "FACE_ABSENT",
        "severity": "high",
        "confidence": 0.9,
        "duration_seconds": 5.5,
        "occurrences": 1,
        "evidence_image_base64": _fake_jpeg_base64(),
    }
    payload.update(overrides)
    return payload


def _create_event(client, student_headers, session_id, **overrides):
    payload = _event_payload(session_id, **overrides)
    return client.post(
        "/api/monitoring/events",
        json=payload,
        headers=student_headers,
    ).json()


def _review(client, admin_headers, evidence_id, action, reason=None):
    payload = {"action": action}
    if reason is not None:
        payload["reason"] = reason
    return client.post(
        f"/api/evidence/{evidence_id}/review",
        json=payload,
        headers=admin_headers,
    ).json()


def _setup_reviewed_action(
    client,
    admin_user,
    student_user,
    student_profile,
    action="CONFIRMED",
    reason=None,
    **event_overrides,
):
    """Creates an active exam + student session + monitoring event (with
    evidence), reviews it once, and returns everything needed for
    assertions.

    Returns (admin_headers, student_headers, exam, session, event, review).
    """
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])
    event = _create_event(client, student_headers, session["id"], **event_overrides)
    review = _review(client, admin_headers, event["evidence"]["id"], action, reason)
    return admin_headers, student_headers, exam, session, event, review


# ---------------------------------------------------------------------------
# Core retrieval / authorization
# ---------------------------------------------------------------------------


def test_admin_can_retrieve_audit_history(client, admin_user, student_user, student_profile):
    admin_headers, _, exam, session, event, review = _setup_reviewed_action(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/audit", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == review["action"]["id"]
    assert item["event_id"] == event["id"]
    assert item["action"] == "CONFIRMED"


def test_unauthenticated_request_returns_401(client):
    response = client.get("/api/audit")
    assert response.status_code == 401


def test_student_request_returns_403(client, admin_user, student_user, student_profile):
    _, student_headers, _, _, _, _ = _setup_reviewed_action(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/audit", headers=student_headers)
    assert response.status_code == 403


def test_empty_audit_history_returns_valid_empty_response(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.get("/api/audit", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["total_pages"] == 0


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_confirmed_filter_works(client, admin_user, student_user, student_profile):
    admin_headers, _, _, _, _, _ = _setup_reviewed_action(
        client, admin_user, student_user, student_profile, action="CONFIRMED"
    )

    matching = client.get("/api/audit?action=CONFIRMED", headers=admin_headers)
    assert matching.status_code == 200
    assert len(matching.json()["items"]) == 1

    non_matching = client.get("/api/audit?action=IGNORED", headers=admin_headers)
    assert non_matching.status_code == 200
    assert non_matching.json()["items"] == []


def test_ignored_filter_works(client, admin_user, student_user, student_profile):
    admin_headers, _, _, _, _, _ = _setup_reviewed_action(
        client, admin_user, student_user, student_profile, action="IGNORED"
    )

    matching = client.get("/api/audit?action=IGNORED", headers=admin_headers)
    assert len(matching.json()["items"]) == 1

    non_matching = client.get("/api/audit?action=CONFIRMED", headers=admin_headers)
    assert non_matching.json()["items"] == []


# ---------------------------------------------------------------------------
# Pagination and ordering
# ---------------------------------------------------------------------------


def test_pagination_works(client, admin_user, student_user, student_profile):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])

    for _ in range(3):
        event = _create_event(client, student_headers, session["id"])
        _review(client, admin_headers, event["evidence"]["id"], "CONFIRMED")

    page_1 = client.get("/api/audit?page=1&page_size=2", headers=admin_headers).json()
    assert len(page_1["items"]) == 2
    assert page_1["total"] == 3
    assert page_1["total_pages"] == 2
    assert page_1["page"] == 1
    assert page_1["page_size"] == 2

    page_2 = client.get("/api/audit?page=2&page_size=2", headers=admin_headers).json()
    assert len(page_2["items"]) == 1
    assert page_2["page"] == 2

    ids_page_1 = {item["id"] for item in page_1["items"]}
    ids_page_2 = {item["id"] for item in page_2["items"]}
    assert ids_page_1.isdisjoint(ids_page_2)


def test_invalid_page_returns_422(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    assert client.get("/api/audit?page=0", headers=admin_headers).status_code == 422
    assert client.get("/api/audit?page=-1", headers=admin_headers).status_code == 422


def test_invalid_page_size_returns_422(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    assert client.get("/api/audit?page_size=0", headers=admin_headers).status_code == 422
    assert client.get("/api/audit?page_size=101", headers=admin_headers).status_code == 422


def test_results_ordered_newest_first(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])

    action_ids = []
    for _ in range(3):
        event = _create_event(client, student_headers, session["id"])
        review = _review(client, admin_headers, event["evidence"]["id"], "CONFIRMED")
        action_ids.append(review["action"]["id"])

    for offset, action_id in enumerate(action_ids):
        row = db_session.get(AdminAction, action_id)
        row.created_at = datetime(2026, 1, 1, 12, offset, 0)
    db_session.commit()

    response = client.get("/api/audit", headers=admin_headers)
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == list(reversed(action_ids))


def test_id_provides_deterministic_tiebreak_for_identical_timestamps(
    client, admin_user, student_user, student_profile, db_session
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])

    action_ids = []
    for _ in range(3):
        event = _create_event(client, student_headers, session["id"])
        review = _review(client, admin_headers, event["evidence"]["id"], "CONFIRMED")
        action_ids.append(review["action"]["id"])

    same_time = datetime(2026, 1, 1, 12, 0, 0)
    for action_id in action_ids:
        row = db_session.get(AdminAction, action_id)
        row.created_at = same_time
    db_session.commit()

    response = client.get("/api/audit", headers=admin_headers)
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == list(reversed(action_ids))

    response_again = client.get("/api/audit", headers=admin_headers)
    ids_again = [item["id"] for item in response_again.json()["items"]]
    assert ids_again == ids


# ---------------------------------------------------------------------------
# Data shape
# ---------------------------------------------------------------------------


def test_admin_username_is_returned(client, admin_user, student_user, student_profile):
    admin_headers, _, _, _, _, _ = _setup_reviewed_action(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/audit", headers=admin_headers)
    item = response.json()["items"][0]
    assert item["admin_username"] == "admin1"


def test_event_type_severity_session_are_returned(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, _, session, event, _ = _setup_reviewed_action(
        client,
        admin_user,
        student_user,
        student_profile,
        event_type="FACE_ABSENT",
        severity="high",
    )

    response = client.get("/api/audit", headers=admin_headers)
    item = response.json()["items"][0]
    assert item["event_type"] == "FACE_ABSENT"
    assert item["severity"] == "high"
    assert item["session_id"] == session["id"]


def test_student_identity_is_returned(client, admin_user, student_user, student_profile):
    admin_headers, _, _, _, _, _ = _setup_reviewed_action(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/audit", headers=admin_headers)
    item = response.json()["items"][0]
    assert item["student_id"] == student_profile.student_id
    assert item["student_full_name"] == student_profile.full_name


def test_exam_identity_is_returned(client, admin_user, student_user, student_profile):
    admin_headers, _, exam, _, _, _ = _setup_reviewed_action(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/audit", headers=admin_headers)
    item = response.json()["items"][0]
    assert item["exam_id"] == exam["id"]
    assert item["exam_title"] == exam["title"]


def test_review_reason_is_returned_when_present(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, _, _, _, _ = _setup_reviewed_action(
        client,
        admin_user,
        student_user,
        student_profile,
        action="IGNORED",
        reason="False positive after review",
    )

    response = client.get("/api/audit", headers=admin_headers)
    item = response.json()["items"][0]
    assert item["reason"] == "False positive after review"


def test_missing_reason_is_represented_safely(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, _, _, _, _ = _setup_reviewed_action(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/audit", headers=admin_headers)
    item = response.json()["items"][0]
    assert item["reason"] is None


# ---------------------------------------------------------------------------
# Repeated reviews / history integrity
# ---------------------------------------------------------------------------


def test_repeated_reviews_produce_separate_audit_entries(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])
    event = _create_event(client, student_headers, session["id"])
    evidence_id = event["evidence"]["id"]

    _review(client, admin_headers, evidence_id, "CONFIRMED")
    _review(client, admin_headers, evidence_id, "IGNORED", reason="Reconsidered")

    response = client.get("/api/audit", headers=admin_headers)
    body = response.json()
    assert body["total"] == 2
    actions = sorted(item["action"] for item in body["items"])
    assert actions == ["CONFIRMED", "IGNORED"]


def test_previous_audit_entries_are_never_overwritten(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])
    event = _create_event(client, student_headers, session["id"])
    evidence_id = event["evidence"]["id"]

    first = _review(client, admin_headers, evidence_id, "CONFIRMED", reason="Initial review")
    _review(client, admin_headers, evidence_id, "CONFIRMED")

    response = client.get("/api/audit", headers=admin_headers)
    items = {item["id"]: item for item in response.json()["items"]}
    assert items[first["action"]["id"]]["reason"] == "Initial review"


# ---------------------------------------------------------------------------
# Security / data leakage
# ---------------------------------------------------------------------------


def test_password_hash_never_returned(client, admin_user, student_user, student_profile):
    admin_headers, _, _, _, _, _ = _setup_reviewed_action(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/audit", headers=admin_headers)
    body = response.json()
    assert "password_hash" not in body
    for item in body["items"]:
        assert "password_hash" not in item


def test_image_path_never_returned(client, admin_user, student_user, student_profile):
    admin_headers, _, _, _, _, _ = _setup_reviewed_action(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/audit", headers=admin_headers)
    body = response.json()
    assert "image_path" not in body
    for item in body["items"]:
        assert "image_path" not in item


# ---------------------------------------------------------------------------
# Regression: Phase 7A / 7B / 7C still function correctly
# ---------------------------------------------------------------------------


def test_existing_review_endpoint_still_functional(
    client, admin_user, student_user, student_profile
):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    session = _start_session(client, student_headers, exam["id"])
    event = _create_event(client, student_headers, session["id"])

    response = client.post(
        f"/api/evidence/{event['evidence']['id']}/review",
        json={"action": "CONFIRMED"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"


def test_existing_monitoring_events_listing_still_functional(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, _, session, event, _ = _setup_reviewed_action(
        client, admin_user, student_user, student_profile
    )

    response = client.get("/api/monitoring/events", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == event["id"]
    assert body["items"][0]["status"] == "CONFIRMED"


def test_existing_dashboard_summary_still_functional(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, _, _, _, _ = _setup_reviewed_action(
        client, admin_user, student_user, student_profile, action="CONFIRMED"
    )

    response = client.get("/api/admin/dashboard/summary", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["confirmed_events"] == 1
    assert body["total_review_actions"] == 1
