from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from authstatus_api.backups.router import router as backups_router
from authstatus_api.errors import register_exception_handlers
from authstatus_api.governance.router import router as governance_router
from authstatus_api.observability.logging import (
    configure_application_logging,
)
from authstatus_api.pdf_intake.router import (
    router as pdf_intake_router,
)
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.registered_options.router import (
    router as registered_options_router,
)
from authstatus_api.routers.analytics import router as analytics_router
from authstatus_api.routers.auths import router as auths_router
from authstatus_api.routers.security import router as security_router
from authstatus_api.settings import get_settings
from authstatus_api.system.router import router as system_router

CORS_ALLOWED_METHODS = [
    "GET",
    "POST",
    "PATCH",
    "DELETE",
]

CORS_ALLOWED_HEADERS = [
    "Content-Type",
    "X-CSRF-Token",
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_application_logging(
        environment=settings.app_environment,
    )

    production = settings.app_environment == "production"

    api = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        debug=settings.app_debug,
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
    )

    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
        expose_headers=["X-CareQueue-Session-Expires-At"],
    )

    if settings.app_environment == "production":
        trusted_hosts = sorted(
            {
                hostname
                for origin in settings.cors_origins
                if (hostname := urlsplit(origin).hostname) is not None
            }
        )

        api.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=trusted_hosts,
        )

    register_exception_handlers(api)

    @api.get("/api/health")
    @api.get("/api/health/live")
    def health_check() -> dict[str, str]:
        return {
            "status": "ok",
        }

    @api.get("/api/health/ready")
    def readiness_check(  # pyright: ignore[reportUnusedFunction]
        response: Response,
    ) -> dict[str, str]:
        try:
            with get_conn() as conn:
                conn.execute("SELECT 1").fetchone()
        except Exception:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "unavailable"}

        return {"status": "ok"}

    api.include_router(security_router)
    api.include_router(governance_router)
    api.include_router(backups_router)
    api.include_router(system_router)
    api.include_router(auths_router)
    api.include_router(analytics_router)
    api.include_router(registered_options_router)
    api.include_router(pdf_intake_router)

    return api


app = create_app()
