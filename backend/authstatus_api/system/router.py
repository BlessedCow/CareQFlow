from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from authstatus_api.persistence.connections import get_conn
from authstatus_api.security.dependencies import require_role
from authstatus_api.system.schemas import (
    EndpointAccess,
    EndpointListResponse,
    EndpointStatus,
    EndpointStatusResponse,
)

router = APIRouter(
    prefix="/api/admin/system",
    tags=["admin-system"],
)

AdminUserDependency = Depends(require_role("Admin"))

PUBLIC_ENDPOINTS = {
    ("GET", "/api/health"),
    ("GET", "/api/health/live"),
    ("GET", "/api/health/ready"),
    ("POST", "/api/security/login"),
    ("POST", "/api/security/login/mfa/verify"),
}

INITIAL_SETUP_ENDPOINTS = {
    ("GET", "/api/security/setup-initial-admin/status"),
    ("POST", "/api/security/setup-initial-admin"),
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
    ("GET", "/api/security/users"),
    ("PATCH", "/api/security/users/{user_id}"),
    ("POST", "/api/admin/system/backups"),
    ("POST", "/api/admin/system/backups/recovery/stage"),
    ("POST", "/api/admin/system/backups/verify"),
    ("POST", "/api/registered-options"),
    ("POST", "/api/security/users"),
    ("POST", "/api/security/users/{user_id}/reset-mfa"),
    ("POST", "/api/security/users/{user_id}/reset-password"),
}

PROBEABLE_ENDPOINTS = {
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
}


def _endpoint_access(
    *,
    method: str,
    path: str,
) -> EndpointAccess:
    endpoint = (method, path)

    if endpoint in PUBLIC_ENDPOINTS:
        return "public"

    if endpoint in INITIAL_SETUP_ENDPOINTS:
        return "initial_setup"

    if endpoint in ADMIN_UR_ENDPOINTS:
        return "admin_ur"

    if endpoint in ADMIN_ENDPOINTS:
        return "admin"

    return "authenticated"


def _database_is_ready() -> bool:
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception:
        return False

    return True


def _endpoint_status(
    *,
    path: str,
    database_ready: bool,
) -> EndpointStatus:
    if path in {"/api/health", "/api/health/live"}:
        return "operational"

    if path == "/api/health/ready":
        return "operational" if database_ready else "unavailable"

    return "registered"


@router.get(
    "/endpoints",
    response_model=EndpointListResponse,
)
def list_api_endpoints(
    request: Request,
    current_user: dict = AdminUserDependency,
) -> EndpointListResponse:
    del current_user

    database_ready = _database_is_ready()
    endpoints: list[EndpointStatusResponse] = []
    openapi_paths = request.app.openapi().get("paths", {})

    for path, path_operations in openapi_paths.items():
        if not path.startswith("/api/"):
            continue

        for method, operation in path_operations.items():
            normalized_method = method.upper()

            if normalized_method not in {
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
                "OPTIONS",
                "HEAD",
            }:
                continue

            tags = operation.get("tags", [])

            endpoints.append(
                EndpointStatusResponse(
                    path=path,
                    methods=[normalized_method],
                    group=(str(tags[0]) if tags else "ungrouped"),
                    access=_endpoint_access(
                        method=normalized_method,
                        path=path,
                    ),
                    status=_endpoint_status(
                        path=path,
                        database_ready=database_ready,
                    ),
                    probeable=path in PROBEABLE_ENDPOINTS,
                )
            )

    endpoints.sort(
        key=lambda endpoint: (
            endpoint.path,
            endpoint.methods,
        )
    )

    return EndpointListResponse(
        endpoints=endpoints,
    )
