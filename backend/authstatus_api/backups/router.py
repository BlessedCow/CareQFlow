from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status

from authstatus_api.audit.service import record_audit_event
from authstatus_api.backups.retention import (
    BackupRetentionError,
    prune_encrypted_database_backups,
)
from authstatus_api.backups.schemas import (
    BackupCreateResponse,
    BackupFileResponse,
    BackupListResponse,
    BackupRetentionResponse,
    BackupVerifyRequest,
    BackupVerifyResponse,
    RecoveryCancelResponse,
    RecoveryStageRequest,
    RecoveryStageResponse,
    RecoveryStatusResponse,
    StagedRecoveryResponse,
)
from authstatus_api.backups.service import (
    BackupConfigError,
    BackupError,
    cancel_staged_database_recovery,
    create_encrypted_database_backup,
    get_staged_database_recovery,
    list_encrypted_database_backups,
    resolve_encrypted_database_backup_path,
    stage_encrypted_database_recovery,
    verify_encrypted_database_backup,
)
from authstatus_api.security.dependencies import require_role
from authstatus_api.settings import get_settings

router = APIRouter(
    prefix="/api/admin/system/backups",
    tags=["admin-system-backups"],
)

AdminUserDependency = Depends(require_role("Admin"))


def _backup_file_response(backup_path: Path) -> BackupFileResponse:
    file_stat = backup_path.stat()

    return BackupFileResponse(
        filename=backup_path.name,
        size_bytes=file_stat.st_size,
        created_at=datetime.fromtimestamp(
            file_stat.st_mtime,
            tz=UTC,
        ).isoformat(timespec="seconds"),
    )


@router.get("", response_model=BackupListResponse)
def read_encrypted_backups(
    current_user: dict = AdminUserDependency,
) -> BackupListResponse:
    try:
        backups = list_encrypted_database_backups()
    except BackupError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backup storage is unavailable.",
        ) from exc

    return BackupListResponse(
        backups=[BackupFileResponse(**backup) for backup in backups],
    )


@router.post(
    "",
    response_model=BackupCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_manual_restore_point(
    request: Request,
    current_user: dict = AdminUserDependency,
) -> BackupCreateResponse:
    settings = get_settings()

    try:
        backup_path = create_encrypted_database_backup()
        verify_encrypted_database_backup(
            backup_path=backup_path,
        )
    except (BackupConfigError, BackupError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to create and verify the restore point.",
        ) from exc

    retention_deleted: list[str] = []
    retention_protected: list[str] = []
    retention_failed: list[str] = []

    try:
        prune_result = prune_encrypted_database_backups(
            retention_days=settings.backup_retention_days,
            minimum_count=settings.backup_minimum_count,
        )
    except BackupRetentionError:
        retention_failed.append("Backup retention cleanup could not be completed.")
    else:
        retention_deleted = prune_result["deleted"]
        retention_protected = prune_result["protected"]
        retention_failed = [failure["filename"] for failure in prune_result["failed"]]

    record_audit_event(
        action="backup.create",
        resource_type="backup",
        user=current_user,
        metadata={
            "filename": backup_path.name,
            "verified": True,
            "retention_days": settings.backup_retention_days,
            "retention_minimum_count": settings.backup_minimum_count,
            "retention_deleted": retention_deleted,
            "retention_protected": retention_protected,
            "retention_failed": retention_failed,
        },
        request=request,
    )

    return BackupCreateResponse(
        backup=_backup_file_response(backup_path),
        verified=True,
        retention=BackupRetentionResponse(
            retention_days=settings.backup_retention_days,
            minimum_count=settings.backup_minimum_count,
            deleted=retention_deleted,
            protected=retention_protected,
            failed=retention_failed,
        ),
    )


@router.post(
    "/verify",
    response_model=BackupVerifyResponse,
)
def verify_manual_restore_point(
    payload: BackupVerifyRequest,
    request: Request,
    current_user: dict = AdminUserDependency,
) -> BackupVerifyResponse:
    try:
        backup_path = resolve_encrypted_database_backup_path(
            filename=payload.filename,
        )
        verify_encrypted_database_backup(
            backup_path=backup_path,
        )
    except BackupConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backup verification is unavailable.",
        ) from exc
    except BackupError as exc:
        record_audit_event(
            action="backup.verify_failed",
            resource_type="backup",
            user=current_user,
            metadata={
                "filename": payload.filename,
            },
            request=request,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected restore point could not be verified.",
        ) from exc

    record_audit_event(
        action="backup.verify",
        resource_type="backup",
        user=current_user,
        metadata={
            "filename": backup_path.name,
            "verified": True,
        },
        request=request,
    )

    return BackupVerifyResponse(
        filename=backup_path.name,
        verified=True,
    )


@router.get(
    "/recovery",
    response_model=RecoveryStatusResponse,
)
def read_staged_recovery(
    current_user: dict = AdminUserDependency,
) -> RecoveryStatusResponse:
    del current_user

    try:
        recovery_info = get_staged_database_recovery()
    except BackupError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recovery status is unavailable.",
        ) from exc

    if recovery_info is None:
        return RecoveryStatusResponse(
            pending=False,
            recovery=None,
        )

    return RecoveryStatusResponse(
        pending=True,
        recovery=StagedRecoveryResponse(**recovery_info),
    )


@router.post(
    "/recovery/stage",
    response_model=RecoveryStageResponse,
    status_code=status.HTTP_201_CREATED,
)
def stage_database_recovery(
    payload: RecoveryStageRequest,
    request: Request,
    current_user: dict = AdminUserDependency,
) -> RecoveryStageResponse:
    try:
        recovery_info = stage_encrypted_database_recovery(
            filename=payload.filename,
        )
    except BackupError as exc:
        record_audit_event(
            action="recovery.stage_failed",
            resource_type="database_recovery",
            user=current_user,
            metadata={
                "backup_filename": payload.filename,
            },
            request=request,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected restore point could not be staged.",
        ) from exc

    record_audit_event(
        action="recovery.stage",
        resource_type="database_recovery",
        user=current_user,
        metadata={
            "backup_filename": recovery_info["backup_filename"],
            "staged_filename": recovery_info["staged_filename"],
        },
        request=request,
    )

    return RecoveryStageResponse(
        recovery=StagedRecoveryResponse(**recovery_info),
        staged=True,
    )


@router.delete(
    "/recovery",
    response_model=RecoveryCancelResponse,
)
def cancel_database_recovery(
    request: Request,
    current_user: dict = AdminUserDependency,
) -> RecoveryCancelResponse:
    try:
        recovery_info = cancel_staged_database_recovery()
    except BackupError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid staged recovery could be canceled.",
        ) from exc

    record_audit_event(
        action="recovery.cancel",
        resource_type="database_recovery",
        user=current_user,
        metadata={
            "backup_filename": recovery_info["backup_filename"],
            "staged_filename": recovery_info["staged_filename"],
        },
        request=request,
    )

    return RecoveryCancelResponse(
        recovery=StagedRecoveryResponse(**recovery_info),
        canceled=True,
    )
