from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.main import create_app
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_system_route_settings(
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


def test_admin_can_list_registered_api_endpoints(client):
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

    response = client.get("/api/admin/system/endpoints")

    assert response.status_code == 200

    endpoints = response.json()["endpoints"]

    assert endpoints
    assert {
        "path": "/api/health/live",
        "methods": ["GET"],
        "group": "ungrouped",
        "access": "public",
        "status": "operational",
        "probeable": True,
    } in endpoints

    assert {
        "path": "/api/health/ready",
        "methods": ["GET"],
        "group": "ungrouped",
        "access": "public",
        "status": "operational",
        "probeable": True,
    } in endpoints

    assert {
        "path": "/api/admin/system/endpoints",
        "methods": ["GET"],
        "group": "admin-system",
        "access": "admin",
        "status": "registered",
        "probeable": False,
    } in endpoints


def test_admin_can_get_system_info(client):
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

    response = client.get("/api/admin/system/info")

    assert response.status_code == 200
    assert response.json() == {
        "app": "AuthStatus API",
        "version": get_settings().app_version,
    }


def test_endpoint_inventory_includes_mutating_routes_without_calling_them(
    client,
):
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

    response = client.get("/api/admin/system/endpoints")

    assert response.status_code == 200

    endpoints = response.json()["endpoints"]

    backup_create_route = next(
        endpoint
        for endpoint in endpoints
        if endpoint["path"] == "/api/admin/system/backups"
        and endpoint["methods"] == ["POST"]
    )

    assert backup_create_route == {
        "path": "/api/admin/system/backups",
        "methods": ["POST"],
        "group": "admin-system-backups",
        "access": "admin",
        "status": "registered",
        "probeable": False,
    }


def test_readiness_endpoint_is_unavailable_when_database_probe_fails(
    client,
):
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

    with patch(
        "authstatus_api.system.router.get_conn",
        side_effect=RuntimeError("sensitive database details"),
    ):
        response = client.get("/api/admin/system/endpoints")

    assert response.status_code == 200
    assert "sensitive database details" not in response.text

    readiness_endpoint = next(
        endpoint
        for endpoint in response.json()["endpoints"]
        if endpoint["path"] == "/api/health/ready"
    )

    assert readiness_endpoint["status"] == "unavailable"


def test_non_admin_cannot_list_api_endpoints(client):
    create_user(
        "ur@example.com",
        "correct horse battery staple",
        role="UR",
    )
    login_headers(
        client,
        username="ur@example.com",
        password="correct horse battery staple",
    )

    response = client.get("/api/admin/system/endpoints")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Operation not permitted for this role.",
    }


def test_unauthenticated_user_cannot_list_api_endpoints(client):
    response = client.get("/api/admin/system/endpoints")

    assert response.status_code == 401
