from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from authstatus_api.errors import register_exception_handlers
from authstatus_api.observability.logging import (
    configure_application_logging,
)
from authstatus_api.pdf_intake.router import (
    router as pdf_intake_router,
)
from authstatus_api.persistence.schema import init_db
from authstatus_api.registered_options.router import (
    router as registered_options_router,
)
from authstatus_api.routers.analytics import router as analytics_router
from authstatus_api.routers.auths import router as auths_router
from authstatus_api.routers.security import router as security_router
from authstatus_api.settings import get_settings

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

    api = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
    )

    register_exception_handlers(api)

    @api.get("/api/health")
    def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    api.include_router(security_router)
    api.include_router(auths_router)
    api.include_router(analytics_router)
    api.include_router(registered_options_router)
    api.include_router(pdf_intake_router)

    return api


app = create_app()
