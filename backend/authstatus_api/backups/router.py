from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status

from authstatus_api.audit.service import record_audit_event
from authstatus_api.backups.schemas import (
    BackupCreateResponse,
    BackupFileResponse,
    BackupListResponse,
    BackupVerifyRequest,
    BackupVerifyResponse,
)
from authstatus_api.backups.service import (
    BackupConfigError,
    BackupError,
    create_encrypted_database_backup,
    list_encrypted_database_backups,
    resolve_encrypted_database_backup_path,
    verify_encrypted_database_backup,
)
from authstatus_api.security.dependencies import require_role

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

    record_audit_event(
        action="backup.create",
        resource_type="backup",
        user=current_user,
        metadata={
            "filename": backup_path.name,
            "verified": True,
        },
        request=request,
    )

    return BackupCreateResponse(
        backup=_backup_file_response(backup_path),
        verified=True,
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
