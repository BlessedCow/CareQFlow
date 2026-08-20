from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.main import create_app
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings

EXPECTED_API_ENDPOINTS = {
    ("DELETE", "/api/admin/system/backups/recovery"),
    ("DELETE", "/api/auths/{auth_id}"),
    ("DELETE", "/api/auths/{auth_id}/documents/{document_id}"),
    ("DELETE", "/api/auths/{auth_id}/events/{event_id}"),
    ("DELETE", "/api/registered-options/{option_id}"),
    ("DELETE", "/api/security/mfa/trusted-devices"),
    ("GET", "/api/admin/system/backups"),
    ("GET", "/api/admin/system/backups/recovery"),
    ("GET", "/api/admin/system/endpoints"),
    ("GET", "/api/analytics/summary"),
    ("GET", "/api/auths"),
    ("GET", "/api/auths/{auth_id}"),
    ("GET", "/api/auths/{auth_id}/documents"),
    ("GET", "/api/auths/{auth_id}/documents/{document_id}/pdf"),
    ("GET", "/api/auths/{auth_id}/events"),
    ("GET", "/api/health"),
    ("GET", "/api/health/live"),
    ("GET", "/api/health/ready"),
    ("GET", "/api/registered-options"),
    ("GET", "/api/security/audit-events"),
    ("GET", "/api/security/me"),
    ("GET", "/api/security/mfa/status"),
    ("GET", "/api/security/monitoring/summary"),
    ("GET", "/api/security/setup-initial-admin/status"),
    ("GET", "/api/security/users"),
    ("PATCH", "/api/auths/{auth_id}"),
    ("PATCH", "/api/auths/{auth_id}/events/{event_id}"),
    ("PATCH", "/api/security/users/{user_id}"),
    ("POST", "/api/admin/system/backups"),
    ("POST", "/api/admin/system/backups/recovery/stage"),
    ("POST", "/api/admin/system/backups/verify"),
    ("POST", "/api/auths"),
    ("POST", "/api/auths/{auth_id}/documents"),
    ("POST", "/api/auths/{auth_id}/events"),
    ("POST", "/api/pdf-intake/preview"),
    ("POST", "/api/registered-options"),
    ("POST", "/api/security/audit-events/verify-integrity"),
    ("POST", "/api/security/change-password"),
    ("POST", "/api/security/login"),
    ("POST", "/api/security/login/mfa/verify"),
    ("POST", "/api/security/logout"),
    ("POST", "/api/security/mfa/enroll"),
    ("POST", "/api/security/mfa/enroll/confirm"),
    ("POST", "/api/security/session/renew"),
    ("POST", "/api/security/setup-initial-admin"),
    ("POST", "/api/security/users"),
    ("POST", "/api/security/users/{user_id}/reset-mfa"),
    ("POST", "/api/security/users/{user_id}/reset-password"),
}

PUBLIC_ENDPOINTS = {
    ("GET", "/api/health"),
    ("GET", "/api/health/live"),
    ("GET", "/api/health/ready"),
    ("GET", "/api/security/setup-initial-admin/status"),
    ("POST", "/api/security/setup-initial-admin"),
    ("POST", "/api/security/login"),
    ("POST", "/api/security/login/mfa/verify"),
}

AUTHENTICATED_ENDPOINTS = {
    ("DELETE", "/api/security/mfa/trusted-devices"),
    ("GET", "/api/analytics/summary"),
    ("GET", "/api/auths"),
    ("GET", "/api/auths/{auth_id}"),
    ("GET", "/api/auths/{auth_id}/documents"),
    ("GET", "/api/auths/{auth_id}/documents/{document_id}/pdf"),
    ("GET", "/api/auths/{auth_id}/events"),
    ("GET", "/api/registered-options"),
    ("GET", "/api/security/me"),
    ("GET", "/api/security/mfa/status"),
    ("POST", "/api/security/change-password"),
    ("POST", "/api/security/logout"),
    ("POST", "/api/security/mfa/enroll"),
    ("POST", "/api/security/mfa/enroll/confirm"),
    ("POST", "/api/security/session/renew"),
}

READ_ONLY_SAFE_GET_ENDPOINTS = {
    endpoint for endpoint in AUTHENTICATED_ENDPOINTS if endpoint[0] == "GET"
}

ADMIN_UR_ENDPOINTS = {
    ("DELETE", "/api/auths/{auth_id}"),
    ("DELETE", "/api/auths/{auth_id}/documents/{document_id}"),
    ("DELETE", "/api/auths/{auth_id}/events/{event_id}"),
    ("PATCH", "/api/auths/{auth_id}"),
    ("PATCH", "/api/auths/{auth_id}/events/{event_id}"),
    ("POST", "/api/auths"),
    ("POST", "/api/auths/{auth_id}/documents"),
    ("POST", "/api/auths/{auth_id}/events"),
    ("POST", "/api/pdf-intake/preview"),
}

ADMIN_ENDPOINTS = {
    ("DELETE", "/api/admin/system/backups/recovery"),
    ("DELETE", "/api/registered-options/{option_id}"),
    ("GET", "/api/admin/system/backups"),
    ("GET", "/api/admin/system/backups/recovery"),
    ("GET", "/api/admin/system/endpoints"),
    ("GET", "/api/security/audit-events"),
    ("GET", "/api/security/monitoring/summary"),
    ("GET", "/api/security/users"),
    ("PATCH", "/api/security/users/{user_id}"),
    ("POST", "/api/admin/system/backups"),
    ("POST", "/api/admin/system/backups/recovery/stage"),
    ("POST", "/api/admin/system/backups/verify"),
    ("POST", "/api/registered-options"),
    ("POST", "/api/security/audit-events/verify-integrity"),
    ("POST", "/api/security/users"),
    ("POST", "/api/security/users/{user_id}/reset-mfa"),
    ("POST", "/api/security/users/{user_id}/reset-password"),
}


@pytest.fixture(autouse=True)
def configure_access_control_test_settings(tmp_path, monkeypatch):
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


def auth_headers_for_role(
    client: TestClient,
    role: str,
) -> dict[str, str]:
    username = f"{role.lower().replace(' ', '')}@example.com"
    password = "correct horse battery staple"

    create_user(
        username,
        password,
        role=role,
    )

    response = client.post(
        "/api/security/login",
        json={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 200
    assert client.cookies.get("carequeue_session")

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    return {
        "X-CSRF-Token": csrf_token,
    }


def concrete_path(path: str) -> str:
    return path.format(
        auth_id=999,
        document_id=999,
        event_id=999,
        option_id=999,
        user_id=999,
    )


def test_access_control_matrix_accounts_for_every_api_endpoint():
    app = create_app()

    openapi_paths = app.openapi().get("paths", {})

    registered_endpoints = {
        (method.upper(), path)
        for path, path_operations in openapi_paths.items()
        if path.startswith("/api/")
        for method in path_operations
        if method.upper()
        in {
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
            "HEAD",
        }
    }

    assert registered_endpoints == EXPECTED_API_ENDPOINTS


def test_access_control_matrix_classifies_every_api_endpoint_once():
    access_groups = (
        PUBLIC_ENDPOINTS,
        AUTHENTICATED_ENDPOINTS,
        ADMIN_UR_ENDPOINTS,
        ADMIN_ENDPOINTS,
    )

    classified_endpoints = set().union(*access_groups)

    assert classified_endpoints == EXPECTED_API_ENDPOINTS

    for index, access_group in enumerate(access_groups):
        other_endpoints = set().union(
            *(
                other_group
                for other_index, other_group in enumerate(access_groups)
                if other_index != index
            )
        )

        assert access_group.isdisjoint(other_endpoints)


@pytest.mark.parametrize("role", ["UR", "Read Only"])
@pytest.mark.parametrize("method,path", sorted(ADMIN_ENDPOINTS))
def test_admin_endpoints_reject_non_admin_roles(
    client,
    role,
    method,
    path,
):
    response = client.request(
        method,
        concrete_path(path),
        headers=auth_headers_for_role(client, role),
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Operation not permitted for this role.",
    }


@pytest.mark.parametrize("method,path", sorted(ADMIN_UR_ENDPOINTS))
def test_admin_ur_endpoints_reject_read_only_role(
    client,
    method,
    path,
):
    response = client.request(
        method,
        concrete_path(path),
        headers=auth_headers_for_role(client, "Read Only"),
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Operation not permitted for this role.",
    }


@pytest.mark.parametrize("role", ["Admin", "UR"])
@pytest.mark.parametrize("method,path", sorted(ADMIN_UR_ENDPOINTS))
def test_admin_ur_endpoints_allow_authorized_roles(
    client,
    role,
    method,
    path,
):
    response = client.request(
        method,
        concrete_path(path),
        headers=auth_headers_for_role(client, role),
        json={} if method in {"POST", "PATCH"} else None,
    )

    assert response.status_code not in {401, 403}


@pytest.mark.parametrize(
    "method,path",
    sorted(READ_ONLY_SAFE_GET_ENDPOINTS),
)
def test_read_only_role_can_reach_authenticated_get_endpoints(
    client,
    method,
    path,
):
    response = client.request(
        method,
        concrete_path(path),
        headers=auth_headers_for_role(client, "Read Only"),
    )

    assert response.status_code not in {401, 403}
