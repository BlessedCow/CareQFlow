from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

EndpointAccess = Literal[
    "public",
    "initial_setup",
    "authenticated",
    "admin_ur",
    "admin",
]

EndpointStatus = Literal[
    "operational",
    "unavailable",
    "registered",
]


class EndpointStatusResponse(BaseModel):
    path: str
    methods: list[str]
    group: str
    access: EndpointAccess
    status: EndpointStatus
    probeable: bool


class EndpointListResponse(BaseModel):
    endpoints: list[EndpointStatusResponse]


class SystemInfoResponse(BaseModel):
    app: str
    version: str
