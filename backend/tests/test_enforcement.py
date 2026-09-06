from datetime import datetime, timedelta

from app.core.security import hash_password
from app.db.models import EnforcementAction, ExamSession, Student, User


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_active_exam(client, admin_headers, title="Sample Exam", duration_minutes=30):
    exam = client.post(
        "/api/exams",
        json={"title": title, "description": "A sample exam", "duration_minutes": duration_minutes},
        headers=admin_headers,
    ).json()
    client.patch(
        f"/api/exams/{exam['id']}/status", json={"status": "active"}, headers=admin_headers
    )
    return exam


def _create_question(client, admin_headers, exam_id, **overrides):
    payload = {
        "question_text": "What is 2 + 2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_answer": "B",
    }
    payload.update(overrides)
    return client.post(f"/api/exams/{exam_id}/questions", json=payload, headers=admin_headers).json()


def _start_session(client, student_headers, exam_id):
    return client.post(
        f"/api/student/exams/{exam_id}/start", headers=student_headers
    ).json()


def _enforce(client, admin_headers, session_id, action_type, **overrides):
    payload = {
        "session_id": session_id,
        "action_type": action_type,
        "reason": "Confirmed violation after evidence review",
    }
    payload.update(overrides)
    return client.post("/api/enforcement/actions", json=payload, headers=admin_headers)


def _create_event(client, student_headers, session_id):
    return client.post(
        "/api/monitoring/events",
        json={
            "session_id": session_id,
            "event_type": "HEAD_LEFT",
            "severity": "medium",
            "confidence": 0.87,
            "duration_seconds": 4.2,
            "occurrences": 3,
        },
        headers=student_headers,
    ).json()


def _bootstrap(client, admin_user, student_user, student_profile):
    """Active exam with one question + an in-progress student session.

    Returns (admin_headers, student_headers, exam, session, question).
    """
    admin_headers = _auth_headers(client, "admin1", "adminpass123")
    student_headers = _auth_headers(client, "student1", "studentpass123")
    exam = _create_active_exam(client, admin_headers)
    question = _create_question(client, admin_headers, exam["id"])
    session = _start_session(client, student_headers, exam["id"])
    return admin_headers, student_headers, exam, session, question


def _expire_block(db_session, action_id):
    """Pushes a BLOCK row's deadline into the past (lazy expiry)."""
    block = db_session.get(EnforcementAction, action_id)
    block.blocked_until = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()


def _force_session_status(db_session, session_id, status_value):
    session_row = db_session.get(ExamSession, session_id)
    session_row.status = status_value
    db_session.commit()


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_unauthenticated_requests_are_rejected(client):
    assert client.get("/api/enforcement/actions").status_code == 401
    assert (
        client.post(
            "/api/enforcement/actions",
            json={"session_id": 1, "action_type": "BLOCK", "reason": "whatever"},
        ).status_code
        == 401
    )
    assert client.post("/api/enforcement/actions/1/lift").status_code == 401


def test_student_cannot_access_enforcement_endpoints(
    client, admin_user, student_user, student_profile
):
    admin_headers, student_headers, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    _enforce(client, admin_headers, session["id"], "BLOCK", block_minutes=5)

    payload = {"session_id": session["id"], "action_type": "BLOCK", "reason": "not allowed"}
    assert (
        client.post("/api/enforcement/actions", json=payload, headers=student_headers).status_code
        == 403
    )
    assert client.get("/api/enforcement/actions", headers=student_headers).status_code == 403
    assert (
        client.post("/api/enforcement/actions/1/lift", headers=student_headers).status_code == 403
    )


# ---------------------------------------------------------------------------
# BLOCK
# ---------------------------------------------------------------------------


def test_admin_can_block_in_progress_session(client, admin_user, student_user, student_profile):
    admin_headers, _, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )

    response = _enforce(client, admin_headers, session["id"], "BLOCK", block_minutes=10)

    assert response.status_code == 201
    body = response.json()
    assert body["action_type"] == "BLOCK"
    assert body["status"] == "ACTIVE"
    assert body["effective_status"] == "ACTIVE"
    assert body["blocked_until"] is not None
    assert body["session_id"] == session["id"]
    assert body["admin_username"] == "admin1"
    assert body["student_full_name"] == "Test Student"
    assert body["exam_title"] == exam["title"]
    assert body["reason"] == "Confirmed violation after evidence review"


def test_block_requires_block_minutes(client, admin_user, student_user, student_profile):
    admin_headers, _, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )

    response = _enforce(client, admin_headers, session["id"], "BLOCK")

    assert response.status_code == 422
    assert "block_minutes" in response.json()["detail"]


def test_block_requires_in_progress_session(
    client, db_session, admin_user, student_user, student_profile
):
    admin_headers, _, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    _force_session_status(db_session, session["id"], "submitted")

    response = _enforce(client, admin_headers, session["id"], "BLOCK", block_minutes=5)

    assert response.status_code == 409


def test_blocked_student_cannot_save_answer_or_submit(
    client, db_session, admin_user, student_user, student_profile
):
    admin_headers, student_headers, exam, session, question = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    _enforce(client, admin_headers, session["id"], "BLOCK", block_minutes=10)

    save = client.put(
        f"/api/student/sessions/{session['id']}/answers/{question['id']}",
        json={"selected_answer": "B"},
        headers=student_headers,
    )
    assert save.status_code == 403
    assert "paused by the invigilator" in save.json()["detail"]

    submit = client.post(
        f"/api/student/sessions/{session['id']}/submit", headers=student_headers
    )
    assert submit.status_code == 403
    assert "paused by the invigilator" in submit.json()["detail"]


def test_session_response_exposes_active_block(
    client, db_session, admin_user, student_user, student_profile
):
    admin_headers, student_headers, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    block = _enforce(
        client, admin_headers, session["id"], "BLOCK", block_minutes=10, reason="Looking away"
    ).json()

    body = client.get(
        f"/api/student/sessions/{session['id']}", headers=student_headers
    ).json()
    assert body["active_block"] == {
        "blocked_until": block["blocked_until"],
        "reason": "Looking away",
    }

    # Once the deadline passes the block stops being reported -- the student
    # client's resync clears the pause overlay with no extra endpoint.
    _expire_block(db_session, block["id"])
    body = client.get(
        f"/api/student/sessions/{session['id']}", headers=student_headers
    ).json()
    assert body["active_block"] is None


def test_block_expiry_restores_writes_and_reports_expired(
    client, db_session, admin_user, student_user, student_profile
):
    admin_headers, student_headers, exam, session, question = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    block = _enforce(client, admin_headers, session["id"], "BLOCK", block_minutes=10).json()
    _expire_block(db_session, block["id"])

    save = client.put(
        f"/api/student/sessions/{session['id']}/answers/{question['id']}",
        json={"selected_answer": "B"},
        headers=student_headers,
    )
    assert save.status_code == 200

    submit = client.post(
        f"/api/student/sessions/{session['id']}/submit", headers=student_headers
    )
    assert submit.status_code == 200
    assert submit.json()["status"] == "submitted"

    listing = client.get("/api/enforcement/actions", headers=admin_headers).json()
    assert listing["items"][0]["effective_status"] == "EXPIRED"
    # Append-only audit trail: the stored status is untouched by expiry.
    assert listing["items"][0]["status"] == "ACTIVE"


def test_admin_can_lift_active_block(client, admin_user, student_user, student_profile):
    admin_headers, student_headers, exam, session, question = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    block = _enforce(client, admin_headers, session["id"], "BLOCK", block_minutes=10).json()

    response = client.post(
        f"/api/enforcement/actions/{block['id']}/lift", headers=admin_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "LIFTED"
    assert body["effective_status"] == "LIFTED"

    save = client.put(
        f"/api/student/sessions/{session['id']}/answers/{question['id']}",
        json={"selected_answer": "B"},
        headers=student_headers,
    )
    assert save.status_code == 200


def test_lift_rejects_unknown_expired_and_non_block_actions(
    client, db_session, admin_user, student_user, student_profile
):
    admin_headers, _, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    ufm = _enforce(client, admin_headers, session["id"], "UFM_CASE").json()
    expired_block = _enforce(
        client, admin_headers, session["id"], "BLOCK", block_minutes=10
    ).json()
    active_block = _enforce(
        client, admin_headers, session["id"], "BLOCK", block_minutes=10
    ).json()

    assert (
        client.post("/api/enforcement/actions/99999/lift", headers=admin_headers).status_code
        == 404
    )

    # Only BLOCK rows are liftable.
    response = client.post(f"/api/enforcement/actions/{ufm['id']}/lift", headers=admin_headers)
    assert response.status_code == 409
    assert "Only BLOCK actions" in response.json()["detail"]

    # An expired block no longer has effect, so lifting it is meaningless.
    _expire_block(db_session, expired_block["id"])
    assert (
        client.post(
            f"/api/enforcement/actions/{expired_block['id']}/lift", headers=admin_headers
        ).status_code
        == 409
    )

    # Lifting an already-lifted block is rejected too.
    client.post(f"/api/enforcement/actions/{active_block['id']}/lift", headers=admin_headers)
    assert (
        client.post(
            f"/api/enforcement/actions/{active_block['id']}/lift", headers=admin_headers
        ).status_code
        == 409
    )


# ---------------------------------------------------------------------------
# CANCEL_EXAM
# ---------------------------------------------------------------------------


def test_cancel_in_progress_session(client, admin_user, student_user, student_profile):
    admin_headers, student_headers, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )

    response = _enforce(client, admin_headers, session["id"], "CANCEL_EXAM")

    assert response.status_code == 201
    body = response.json()
    assert body["action_type"] == "CANCEL_EXAM"
    assert body["status"] == "COMPLETED"

    session_body = client.get(
        f"/api/student/sessions/{session['id']}", headers=student_headers
    ).json()
    assert session_body["status"] == "cancelled"
    assert session_body["score"] == 0
    assert session_body["ended_at"] is not None


def test_cancel_submitted_session_voids_score(
    client, admin_user, student_user, student_profile
):
    admin_headers, student_headers, exam, session, question = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    client.put(
        f"/api/student/sessions/{session['id']}/answers/{question['id']}",
        json={"selected_answer": "B"},
        headers=student_headers,
    )
    submit = client.post(
        f"/api/student/sessions/{session['id']}/submit", headers=student_headers
    ).json()
    assert submit["score"] == 100  # 1 of 1 answered correctly

    response = _enforce(client, admin_headers, session["id"], "CANCEL_EXAM")

    assert response.status_code == 201
    session_body = client.get(
        f"/api/student/sessions/{session['id']}", headers=student_headers
    ).json()
    assert session_body["status"] == "cancelled"
    assert session_body["score"] == 0


def test_cancel_twice_is_rejected(client, admin_user, student_user, student_profile):
    admin_headers, _, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )

    assert _enforce(client, admin_headers, session["id"], "CANCEL_EXAM").status_code == 201
    response = _enforce(client, admin_headers, session["id"], "CANCEL_EXAM")
    assert response.status_code == 409


def test_cancel_expired_session_is_rejected(
    client, db_session, admin_user, student_user, student_profile
):
    admin_headers, _, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    _force_session_status(db_session, session["id"], "expired")

    response = _enforce(client, admin_headers, session["id"], "CANCEL_EXAM")

    assert response.status_code == 409


def test_student_cannot_restart_exam_after_cancel(
    client, admin_user, student_user, student_profile
):
    admin_headers, student_headers, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    _enforce(client, admin_headers, session["id"], "CANCEL_EXAM")

    response = client.post(f"/api/student/exams/{exam['id']}/start", headers=student_headers)

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# UFM_CASE
# ---------------------------------------------------------------------------


def test_ufm_case_created_with_student_and_event_link(
    client, admin_user, student_user, student_profile
):
    admin_headers, student_headers, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    event = _create_event(client, student_headers, session["id"])

    response = _enforce(client, admin_headers, session["id"], "UFM_CASE", event_id=event["id"])

    assert response.status_code == 201
    body = response.json()
    assert body["action_type"] == "UFM_CASE"
    assert body["status"] == "COMPLETED"
    assert body["effective_status"] == "COMPLETED"
    assert body["event_id"] == event["id"]
    assert body["student_id"] == student_profile.id


def test_ufm_case_allowed_on_finalized_session(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    _enforce(client, admin_headers, session["id"], "CANCEL_EXAM")

    # A UFM case is a student-level academic record: the session's fate
    # (cancelled here) doesn't gate it.
    response = _enforce(client, admin_headers, session["id"], "UFM_CASE")

    assert response.status_code == 201


def test_event_id_must_belong_to_the_target_session(
    client, db_session, admin_user, student_user, student_profile
):
    admin_headers, student_headers, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    second_user = User(
        username="student2",
        password_hash=hash_password("studentpass456"),
        role="student",
        status=True,
    )
    db_session.add(second_user)
    db_session.commit()
    db_session.refresh(second_user)
    second_student = Student(
        user_id=second_user.id,
        student_id="STU-2002",
        full_name="Second Student",
        is_active=True,
    )
    db_session.add(second_student)
    db_session.commit()
    db_session.refresh(second_student)

    second_headers = _auth_headers(client, "student2", "studentpass456")
    second_exam = _create_active_exam(client, admin_headers, title="Second Exam")
    second_session = _start_session(client, second_headers, second_exam["id"])
    other_event = _create_event(client, second_headers, second_session["id"])

    response = _enforce(
        client, admin_headers, session["id"], "UFM_CASE", event_id=other_event["id"]
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Validation and listing
# ---------------------------------------------------------------------------


def test_reason_is_required_and_session_must_exist(
    client, admin_user, student_user, student_profile
):
    admin_headers, _, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )

    too_short = {
        "session_id": session["id"],
        "action_type": "BLOCK",
        "reason": "ab",
        "block_minutes": 5,
    }
    assert (
        client.post("/api/enforcement/actions", json=too_short, headers=admin_headers).status_code
        == 422
    )

    unknown_session = {
        "session_id": 99999,
        "action_type": "BLOCK",
        "reason": "valid reason",
        "block_minutes": 5,
    }
    assert (
        client.post(
            "/api/enforcement/actions", json=unknown_session, headers=admin_headers
        ).status_code
        == 404
    )


def test_listing_filters_and_pagination(
    client, db_session, admin_user, student_user, student_profile
):
    admin_headers, _, exam, session, _ = _bootstrap(
        client, admin_user, student_user, student_profile
    )
    expired_block = _enforce(
        client, admin_headers, session["id"], "BLOCK", block_minutes=10
    ).json()
    active_block = _enforce(
        client, admin_headers, session["id"], "BLOCK", block_minutes=10
    ).json()
    _enforce(client, admin_headers, session["id"], "CANCEL_EXAM")
    _enforce(client, admin_headers, session["id"], "UFM_CASE")
    _expire_block(db_session, expired_block["id"])

    listing = client.get("/api/enforcement/actions", headers=admin_headers).json()
    assert listing["total"] == 4

    by_type = client.get(
        "/api/enforcement/actions", params={"action_type": "BLOCK"}, headers=admin_headers
    ).json()
    assert by_type["total"] == 2
    assert all(item["action_type"] == "BLOCK" for item in by_type["items"])

    # The status filter matches the EFFECTIVE status the API reports, so an
    # expired block counts as EXPIRED -- the filter lines up with the UI.
    expired = client.get(
        "/api/enforcement/actions", params={"status": "EXPIRED"}, headers=admin_headers
    ).json()
    assert expired["total"] == 1
    assert expired["items"][0]["id"] == expired_block["id"]

    active = client.get(
        "/api/enforcement/actions", params={"status": "ACTIVE"}, headers=admin_headers
    ).json()
    assert active["total"] == 1
    assert active["items"][0]["id"] == active_block["id"]

    by_student = client.get(
        "/api/enforcement/actions",
        params={"student_id": student_profile.id},
        headers=admin_headers,
    ).json()
    assert by_student["total"] == 4

    paged = client.get(
        "/api/enforcement/actions",
        params={"page": 1, "page_size": 3},
        headers=admin_headers,
    ).json()
    assert len(paged["items"]) == 3
    assert paged["total"] == 4
    assert paged["total_pages"] == 2
    # Newest first.
    assert paged["items"][0]["action_type"] == "UFM_CASE"
