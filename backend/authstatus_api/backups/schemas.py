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


class RecoveryStageRequest(BaseModel):
    filename: str

    model_config = ConfigDict(extra="forbid")


class StagedRecoveryResponse(BaseModel):
    backup_filename: str
    staged_filename: str
    staged_at: str


class RecoveryStatusResponse(BaseModel):
    pending: bool
    recovery: StagedRecoveryResponse | None


class RecoveryStageResponse(BaseModel):
    recovery: StagedRecoveryResponse
    staged: bool


class RecoveryCancelResponse(BaseModel):
    recovery: StagedRecoveryResponse
    canceled: bool
