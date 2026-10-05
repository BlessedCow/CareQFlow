from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.main import create_app
from authstatus_api.persistence.connections import get_conn
from authstatus_api.routers import auths as auths_router
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", generate_encryption_key())
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    create_user(
        "ur@example.com",
        "correct horse battery staple",
        role="UR",
    )

    response = client.post(
        "/api/security/login",
        json={
            "username": "ur@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 200

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    return {"X-CSRF-Token": csrf_token}


def _create_auth(client, auth_headers) -> int:
    response = client.post(
        "/api/auths",
        json={
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Pending",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    return int(response.json()["id"])


def _assessment_payload() -> dict:
    return {
        "instrument": "CIWA-Ar",
        "score": 23,
        "assessed_at": "2026-09-01T08:00:00+00:00",
        "loc": "RTC",
    }


def test_create_clinical_assessment_endpoint(client, auth_headers):
    auth_id = _create_auth(client, auth_headers)

    response = client.post(
        f"/api/auths/{auth_id}/clinical-assessments",
        json=_assessment_payload(),
        headers=auth_headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["auth_id"] == auth_id
    assert data["instrument"] == "CIWA-Ar"
    assert data["score"] == 23.0
    assert data["loc"] == "RTC"


def test_create_clinical_assessment_rolls_back_when_audit_write_fails(
    client,
    auth_headers,
    monkeypatch,
):
    auth_id = _create_auth(client, auth_headers)

    with get_conn() as conn:
        before_assessment_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM clinical_assessments
            WHERE auth_id = ?
            """,
            (auth_id,),
        ).fetchone()["count"]

        before_audit_count = conn.execute("""
            SELECT COUNT(*) AS count
            FROM audit_events
            WHERE action = 'clinical_assessment.create'
            """).fetchone()["count"]

    def fail_audit_write(**kwargs):
        raise RuntimeError("Synthetic audit write failure.")

    monkeypatch.setattr(
        auths_router,
        "record_audit_event",
        fail_audit_write,
    )

    with pytest.raises(
        RuntimeError,
        match="Synthetic audit write failure.",
    ):
        client.post(
            f"/api/auths/{auth_id}/clinical-assessments",
            json=_assessment_payload(),
            headers=auth_headers,
        )

    with get_conn() as conn:
        after_assessment_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM clinical_assessments
            WHERE auth_id = ?
            """,
            (auth_id,),
        ).fetchone()["count"]

        after_audit_count = conn.execute("""
            SELECT COUNT(*) AS count
            FROM audit_events
            WHERE action = 'clinical_assessment.create'
            """).fetchone()["count"]

    assert after_assessment_count == before_assessment_count
    assert after_audit_count == before_audit_count


def test_list_clinical_assessments_endpoint(client, auth_headers):
    auth_id = _create_auth(client, auth_headers)

    first = client.post(
        f"/api/auths/{auth_id}/clinical-assessments",
        json={
            "instrument": "PHQ-9",
            "score": 19,
            "assessed_at": "2026-09-04T10:00:00+00:00",
        },
        headers=auth_headers,
    )

    second = client.post(
        f"/api/auths/{auth_id}/clinical-assessments",
        json={
            "instrument": "GAD-7",
            "score": 15,
            "assessed_at": "2026-09-03T10:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get(
        f"/api/auths/{auth_id}/clinical-assessments",
    )

    assert response.status_code == 200
    assert [item["instrument"] for item in response.json()["assessments"]] == [
        "GAD-7",
        "PHQ-9",
    ]


def test_list_clinical_assessments_writes_phi_read_audit_event(
    client,
    auth_headers,
):
    auth_id = _create_auth(client, auth_headers)

    create_response = client.post(
        f"/api/auths/{auth_id}/clinical-assessments",
        json=_assessment_payload(),
        headers=auth_headers,
    )

    assert create_response.status_code == 201

    response = client.get(
        f"/api/auths/{auth_id}/clinical-assessments",
    )

    assert response.status_code == 200

    with get_conn() as conn:
        row = conn.execute("""
            SELECT action, resource_type, resource_id, username, metadata
            FROM audit_events
            WHERE action = 'clinical_assessment.list'
            ORDER BY id DESC
            LIMIT 1
            """).fetchone()

    assert row is not None
    assert row["action"] == "clinical_assessment.list"
    assert row["resource_type"] == "clinical_assessment"
    assert row["resource_id"] is None
    assert row["username"] == "ur@example.com"

    metadata = json.loads(row["metadata"])

    assert metadata == {
        "auth_id": auth_id,
        "result_count": len(response.json()["assessments"]),
    }

    assert "CIWA-Ar" not in row["metadata"]
    assert "23" not in row["metadata"]
    assert "RTC" not in row["metadata"]
    assert "2026-09-01" not in row["metadata"]


def test_missing_auth_clinical_assessment_list_does_not_write_phi_read_event(
    client,
    auth_headers,
):
    with get_conn() as conn:
        before = conn.execute("""
            SELECT COUNT(*) AS count
            FROM audit_events
            WHERE action = 'clinical_assessment.list'
            """).fetchone()["count"]

    response = client.get(
        "/api/auths/999999/clinical-assessments",
    )

    assert response.status_code == 404

    with get_conn() as conn:
        after = conn.execute("""
            SELECT COUNT(*) AS count
            FROM audit_events
            WHERE action = 'clinical_assessment.list'
            """).fetchone()["count"]

    assert after == before


def test_update_clinical_assessment_endpoint(client, auth_headers):
    auth_id = _create_auth(client, auth_headers)

    created = client.post(
        f"/api/auths/{auth_id}/clinical-assessments",
        json=_assessment_payload(),
        headers=auth_headers,
    )

    assert created.status_code == 201

    assessment_id = created.json()["id"]

    response = client.patch(
        f"/api/auths/{auth_id}/clinical-assessments/{assessment_id}",
        json={"score": 18},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["score"] == 18.0


def test_update_clinical_assessment_rolls_back_when_audit_write_fails(
    client,
    auth_headers,
    monkeypatch,
):
    auth_id = _create_auth(client, auth_headers)

    created = client.post(
        f"/api/auths/{auth_id}/clinical-assessments",
        json=_assessment_payload(),
        headers=auth_headers,
    )

    assert created.status_code == 201

    assessment_id = created.json()["id"]

    with get_conn() as conn:
        before_assessment = conn.execute(
            """
            SELECT *
            FROM clinical_assessments
            WHERE auth_id = ? AND id = ?
            """,
            (
                auth_id,
                assessment_id,
            ),
        ).fetchone()

        before_audit_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM audit_events
            WHERE action = 'clinical_assessment.update'
              AND resource_id = ?
            """,
            (assessment_id,),
        ).fetchone()["count"]

    assert before_assessment is not None

    def fail_audit_write(**kwargs):
        raise RuntimeError("Synthetic audit write failure.")

    monkeypatch.setattr(
        auths_router,
        "record_audit_event",
        fail_audit_write,
    )

    with pytest.raises(
        RuntimeError,
        match="Synthetic audit write failure.",
    ):
        client.patch(
            f"/api/auths/{auth_id}/clinical-assessments/{assessment_id}",
            json={
                "instrument": "COWS",
                "score": 18,
                "loc": "3.7-WM",
                "source": "clinical",
            },
            headers=auth_headers,
        )

    with get_conn() as conn:
        after_assessment = conn.execute(
            """
            SELECT *
            FROM clinical_assessments
            WHERE auth_id = ? AND id = ?
            """,
            (
                auth_id,
                assessment_id,
            ),
        ).fetchone()

        after_audit_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM audit_events
            WHERE action = 'clinical_assessment.update'
              AND resource_id = ?
            """,
            (assessment_id,),
        ).fetchone()["count"]

    assert after_assessment is not None
    assert dict(after_assessment) == dict(before_assessment)
    assert after_audit_count == before_audit_count


def test_delete_clinical_assessment_endpoint(client, auth_headers):
    auth_id = _create_auth(client, auth_headers)

    created = client.post(
        f"/api/auths/{auth_id}/clinical-assessments",
        json=_assessment_payload(),
        headers=auth_headers,
    )

    assessment_id = created.json()["id"]

    response = client.delete(
        f"/api/auths/{auth_id}/clinical-assessments/{assessment_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "deleted": True,
        "id": assessment_id,
    }


def test_delete_clinical_assessment_rolls_back_when_audit_write_fails(
    client,
    auth_headers,
    monkeypatch,
):
    auth_id = _create_auth(client, auth_headers)

    created = client.post(
        f"/api/auths/{auth_id}/clinical-assessments",
        json=_assessment_payload(),
        headers=auth_headers,
    )

    assert created.status_code == 201

    assessment_id = created.json()["id"]

    with get_conn() as conn:
        before_assessment = conn.execute(
            """
            SELECT *
            FROM clinical_assessments
            WHERE auth_id = ? AND id = ?
            """,
            (
                auth_id,
                assessment_id,
            ),
        ).fetchone()

        before_audit_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM audit_events
            WHERE action = 'clinical_assessment.delete'
              AND resource_id = ?
            """,
            (assessment_id,),
        ).fetchone()["count"]

    assert before_assessment is not None

    def fail_audit_write(**kwargs):
        raise RuntimeError("Synthetic audit write failure.")

    monkeypatch.setattr(
        auths_router,
        "record_audit_event",
        fail_audit_write,
    )

    with pytest.raises(
        RuntimeError,
        match="Synthetic audit write failure.",
    ):
        client.delete(
            f"/api/auths/{auth_id}/clinical-assessments/{assessment_id}",
            headers=auth_headers,
        )

    with get_conn() as conn:
        after_assessment = conn.execute(
            """
            SELECT *
            FROM clinical_assessments
            WHERE auth_id = ? AND id = ?
            """,
            (
                auth_id,
                assessment_id,
            ),
        ).fetchone()

        after_audit_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM audit_events
            WHERE action = 'clinical_assessment.delete'
              AND resource_id = ?
            """,
            (assessment_id,),
        ).fetchone()["count"]

    assert after_assessment is not None
    assert dict(after_assessment) == dict(before_assessment)
    assert after_audit_count == before_audit_count


def test_create_clinical_assessment_rejects_invalid_timestamp(
    client,
    auth_headers,
):
    auth_id = _create_auth(client, auth_headers)

    response = client.post(
        f"/api/auths/{auth_id}/clinical-assessments",
        json={
            "instrument": "CIWA-Ar",
            "score": 23,
            "assessed_at": "not-a-timestamp",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_read_only_user_can_view_clinical_assessments(
    client,
    auth_headers,
):
    auth_id = _create_auth(client, auth_headers)

    created = client.post(
        f"/api/auths/{auth_id}/clinical-assessments",
        json=_assessment_payload(),
        headers=auth_headers,
    )

    assert created.status_code == 201

    client.post(
        "/api/security/logout",
        headers=auth_headers,
    )

    create_user(
        "readonly@example.com",
        "correct horse battery staple",
        role="Read Only",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "readonly@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    response = client.get(
        f"/api/auths/{auth_id}/clinical-assessments",
    )

    assert response.status_code == 200
    assert len(response.json()["assessments"]) == 1


def test_read_only_user_cannot_create_clinical_assessment(
    client,
    auth_headers,
):
    auth_id = _create_auth(client, auth_headers)

    client.post(
        "/api/security/logout",
        headers=auth_headers,
    )

    create_user(
        "readonly@example.com",
        "correct horse battery staple",
        role="Read Only",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "readonly@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    response = client.post(
        f"/api/auths/{auth_id}/clinical-assessments",
        json=_assessment_payload(),
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 403
