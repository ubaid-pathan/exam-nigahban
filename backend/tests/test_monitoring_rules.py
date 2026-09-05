"""Tests for the admin monitoring-rules endpoints."""


def _auth_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_list_monitoring_rules(client, admin_user):
    admin_headers = _auth_headers(client, "admin1", "adminpass123")

    response = client.get("/api/admin/monitoring/rules", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 8
    event_types = {rule["event_type"] for rule in body["items"]}
    assert "HEAD_LEFT" in event_types
    assert "MOBILE_PHONE" in event_types


def test_student_cannot_list_monitoring_rules(client, student_user):
    student_headers = _auth_headers(client, "student1", "studentpass123")

    response = client.get("/api/admin/monitoring/rules", headers=student_headers)

    assert response.status_code == 403


def test_unauthenticated_cannot_list_monitoring_rules(client):
    response = client.get("/api/admin/monitoring/rules")
    assert response.status_code == 401
