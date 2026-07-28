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
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/security/login",
}

PROBEABLE_ENDPOINTS = {
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
}


def _endpoint_access(path: str) -> EndpointAccess:
    if path in PUBLIC_ENDPOINTS:
        return "public"

    if path.startswith("/api/admin/"):
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
                    access=_endpoint_access(path),
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
