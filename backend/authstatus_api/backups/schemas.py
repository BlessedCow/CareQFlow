from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BackupFileResponse(BaseModel):
    filename: str
    size_bytes: int
    created_at: str


class BackupListResponse(BaseModel):
    backups: list[BackupFileResponse]


class BackupCreateResponse(BaseModel):
    backup: BackupFileResponse
    verified: bool


class BackupVerifyRequest(BaseModel):
    filename: str

    model_config = ConfigDict(extra="forbid")


class BackupVerifyResponse(BaseModel):
    filename: str
    verified: bool
