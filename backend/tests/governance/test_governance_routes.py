from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import authstatus_api.governance.repository as governance_repository
import authstatus_api.governance.service as governance_service
from authstatus_api.crypto import generate_encryption_key
from authstatus_api.governance.repository import (
    CURRENT_GOVERNANCE_DOCUMENT_REVISION,
)
from authstatus_api.main import create_app
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
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


def login_headers(
    client: TestClient,
    *,
    username: str,
    password: str,
) -> dict[str, str]:
    response = client.post(
        "/api/security/login",
        json={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 200

    csrf_token = client.cookies.get("carequeue_csrf")
    assert csrf_token

    return {
        "X-CSRF-Token": csrf_token,
    }


def acceptance_payload() -> dict:
    return {
        "organization_name": "Example Facility",
        "deployment_mode": "self_hosted",
        "acknowledge_privacy_security_responsibility": True,
        "acknowledge_required_agreements": True,
        "acknowledge_authorized_access": True,
        "acknowledge_device_and_export_safeguards": True,
        "acknowledge_test_data_requirements": True,
    }


def test_authenticated_user_can_read_incomplete_governance_status(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    login_headers(
        client,
        username="user@example.com",
        password="correct horse battery staple",
    )

    response = client.get("/api/governance/status")

    assert response.status_code == 200
    assert response.json() == {
        "required_version": 1,
        "required_document_revision": CURRENT_GOVERNANCE_DOCUMENT_REVISION,
        "current": False,
        "attestation": None,
    }


def test_admin_can_accept_governance_attestation(client):
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    headers = login_headers(
        client,
        username=admin["username"],
        password="correct horse battery staple",
    )

    response = client.post(
        "/api/governance/attestations",
        json=acceptance_payload(),
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["attestation_version"] == 1
    assert data["organization_name"] == "Example Facility"
    assert data["deployment_mode"] == "self_hosted"
    assert data["accepted_by_user_id"] == admin["id"]
    assert data["accepted_by_username"] == admin["username"]
    assert data["accepted_at"]
    assert data["app_version"] == get_settings().app_version


def test_non_admin_cannot_accept_governance_attestation(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    response = client.post(
        "/api/governance/attestations",
        json=acceptance_payload(),
        headers=login_headers(
            client,
            username="user@example.com",
            password="correct horse battery staple",
        ),
    )

    assert response.status_code == 403


def test_governance_acceptance_requires_every_acknowledgment(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    payload = acceptance_payload()
    payload["acknowledge_required_agreements"] = False

    response = client.post(
        "/api/governance/attestations",
        json=payload,
        headers=login_headers(
            client,
            username="admin@example.com",
            password="correct horse battery staple",
        ),
    )

    assert response.status_code == 422


def test_governance_acceptance_rejects_unknown_fields(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    payload = acceptance_payload()
    payload["accepted_without_reading"] = True

    response = client.post(
        "/api/governance/attestations",
        json=payload,
        headers=login_headers(
            client,
            username="admin@example.com",
            password="correct horse battery staple",
        ),
    )

    assert response.status_code == 422


def test_current_governance_version_cannot_be_accepted_twice(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    headers = login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    first_response = client.post(
        "/api/governance/attestations",
        json=acceptance_payload(),
        headers=headers,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/governance/attestations",
        json=acceptance_payload(),
        headers=headers,
    )

    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": ("The current governance attestation has already " "been accepted.")
    }


def test_obsolete_governance_attestation_blocks_protected_access_until_reaccepted(
    client,
    monkeypatch,
):
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    headers = login_headers(
        client,
        username=admin["username"],
        password="correct horse battery staple",
    )

    first_response = client.post(
        "/api/governance/attestations",
        json=acceptance_payload(),
        headers=headers,
    )

    assert first_response.status_code == 201
    assert first_response.json()["attestation_version"] == 1

    initially_allowed = client.get("/api/auths")

    assert initially_allowed.status_code == 200

    monkeypatch.setattr(
        governance_repository,
        "CURRENT_GOVERNANCE_ATTESTATION_VERSION",
        2,
    )
    monkeypatch.setattr(
        governance_service,
        "CURRENT_GOVERNANCE_ATTESTATION_VERSION",
        2,
    )

    outdated_status = client.get("/api/governance/status")

    assert outdated_status.status_code == 200
    assert outdated_status.json() == {
        "required_version": 2,
        "required_document_revision": CURRENT_GOVERNANCE_DOCUMENT_REVISION,
        "current": False,
        "attestation": None,
    }

    blocked_response = client.get("/api/auths")

    assert blocked_response.status_code == 428
    assert blocked_response.json() == {
        "detail": "Governance attestation required.",
    }

    second_response = client.post(
        "/api/governance/attestations",
        json=acceptance_payload(),
        headers=headers,
    )

    assert second_response.status_code == 201
    assert second_response.json()["attestation_version"] == 2

    allowed_again = client.get("/api/auths")

    assert allowed_again.status_code == 200


def test_protected_routes_require_current_governance_attestation(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    response = client.get("/api/security/users")

    assert response.status_code == 428
    assert response.json() == {
        "detail": "Governance attestation required.",
    }


def test_governance_status_remains_available_before_acceptance(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    response = client.get("/api/governance/status")

    assert response.status_code == 200
    assert response.json()["current"] is False


def test_governance_acceptance_unlocks_protected_routes(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    headers = login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    blocked_response = client.get("/api/security/users")

    assert blocked_response.status_code == 428

    acceptance_response = client.post(
        "/api/governance/attestations",
        json=acceptance_payload(),
        headers=headers,
    )

    assert acceptance_response.status_code == 201

    allowed_response = client.get("/api/security/users")

    assert allowed_response.status_code == 200


def test_change_password_remains_available_before_governance_acceptance(
    client,
):
    create_user(
        "temporary@example.com",
        "temporary password value",
        role="Admin",
        must_change_password=True,
    )

    headers = login_headers(
        client,
        username="temporary@example.com",
        password="temporary password value",
    )

    response = client.post(
        "/api/security/change-password",
        json={
            "current_password": "temporary password value",
            "new_password": "permanent password value",
        },
        headers=headers,
    )

    assert response.status_code == 200


def test_authorization_records_require_current_governance_attestation(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    response = client.get("/api/auths")

    assert response.status_code == 428
    assert response.json() == {
        "detail": "Governance attestation required.",
    }


def test_authorization_records_unlock_after_governance_acceptance(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    headers = login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    blocked_response = client.get("/api/auths")

    assert blocked_response.status_code == 428

    acceptance_response = client.post(
        "/api/governance/attestations",
        json=acceptance_payload(),
        headers=headers,
    )

    assert acceptance_response.status_code == 201

    allowed_response = client.get("/api/auths")

    assert allowed_response.status_code == 200
    assert allowed_response.json() == {
        "auths": [],
    }


def test_admin_can_read_governance_attestation_history(client):
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    headers = login_headers(
        client,
        username=admin["username"],
        password="correct horse battery staple",
    )

    acceptance_response = client.post(
        "/api/governance/attestations",
        json=acceptance_payload(),
        headers=headers,
    )

    assert acceptance_response.status_code == 201

    response = client.get(
        "/api/governance/attestations",
        headers=headers,
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 1
    assert history[0]["attestation_version"] == 1
    assert history[0]["organization_name"] == "Example Facility"
    assert history[0]["accepted_by_username"] == admin["username"]


def test_governance_history_requires_completed_governance(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    headers = login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    response = client.get(
        "/api/governance/attestations",
        headers=headers,
    )

    assert response.status_code == 428
    assert response.json() == {
        "detail": "Governance attestation required.",
    }


def test_non_admin_cannot_read_governance_attestation_history(client):
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    user = create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    admin_headers = login_headers(
        client,
        username=admin["username"],
        password="correct horse battery staple",
    )

    acceptance_response = client.post(
        "/api/governance/attestations",
        json=acceptance_payload(),
        headers=admin_headers,
    )

    assert acceptance_response.status_code == 201

    user_headers = login_headers(
        client,
        username=user["username"],
        password="correct horse battery staple",
    )

    response = client.get(
        "/api/governance/attestations",
        headers=user_headers,
    )

    assert response.status_code == 403
