from __future__ import annotations

from fastapi.testclient import TestClient

from authstatus_api.main import create_app
from authstatus_api.settings import get_settings

TRUSTED_ORIGIN = "http://localhost:5173"


def create_test_client(
    monkeypatch,
) -> TestClient:
    monkeypatch.setenv(
        "AUTHSTATUS_CORS_ORIGINS",
        TRUSTED_ORIGIN,
    )
    get_settings.cache_clear()

    return TestClient(create_app())


def test_trusted_origin_preflight_allows_supported_method_and_headers(
    monkeypatch,
):
    with create_test_client(monkeypatch) as client:
        response = client.options(
            "/api/auths",
            headers={
                "Origin": TRUSTED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": ("content-type,x-csrf-token"),
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (TRUSTED_ORIGIN)
    assert response.headers["access-control-allow-credentials"] == "true"

    allowed_methods = {
        method.strip()
        for method in response.headers["access-control-allow-methods"].split(",")
    }

    assert allowed_methods == {
        "GET",
        "POST",
        "PATCH",
        "DELETE",
    }

    allowed_headers = {
        header.strip().lower()
        for header in response.headers["access-control-allow-headers"].split(",")
    }

    assert "content-type" in allowed_headers
    assert "x-csrf-token" in allowed_headers


def test_preflight_rejects_unsupported_method(
    monkeypatch,
):
    with create_test_client(monkeypatch) as client:
        response = client.options(
            "/api/auths",
            headers={
                "Origin": TRUSTED_ORIGIN,
                "Access-Control-Request-Method": "PUT",
            },
        )

    assert response.status_code == 400
    assert response.text == "Disallowed CORS method"


def test_preflight_rejects_unsupported_header(
    monkeypatch,
):
    with create_test_client(monkeypatch) as client:
        response = client.options(
            "/api/auths",
            headers={
                "Origin": TRUSTED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": ("x-unsupported-header"),
            },
        )

    assert response.status_code == 400
    assert response.text == "Disallowed CORS headers"


def test_preflight_rejects_untrusted_origin(
    monkeypatch,
):
    with create_test_client(monkeypatch) as client:
        response = client.options(
            "/api/auths",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 400
    assert response.text == "Disallowed CORS origin"
    assert "access-control-allow-origin" not in response.headers


def test_simple_request_from_trusted_origin_gets_cors_headers(
    monkeypatch,
):
    with create_test_client(monkeypatch) as client:
        response = client.get(
            "/api/health",
            headers={
                "Origin": TRUSTED_ORIGIN,
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (TRUSTED_ORIGIN)
    assert response.headers["access-control-allow-credentials"] == "true"
