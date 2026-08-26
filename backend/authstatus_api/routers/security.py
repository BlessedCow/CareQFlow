from __future__ import annotations

import sqlite3
from ipaddress import ip_address

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)

from authstatus_api.audit.service import list_audit_events, record_audit_event
from authstatus_api.audit.verification import verify_audit_chain
from authstatus_api.security.csrf import (
    generate_csrf_token,
    validate_csrf_request,
)
from authstatus_api.security.dependencies import (
    AuthenticatedUserDependency,
    CurrentUserDependency,
    extract_session_token,
    require_role,
)
from authstatus_api.security.mfa import (
    build_totp_provisioning_uri,
    clear_user_mfa,
    enable_user_mfa,
    generate_totp_secret,
    get_user_mfa_secret,
    store_user_mfa_secret,
    verify_totp_code,
)
from authstatus_api.security.mfa_challenges import (
    consume_mfa_login_challenge,
    create_mfa_login_challenge,
    get_active_mfa_login_challenge_by_token,
)
from authstatus_api.security.monitoring import get_security_monitoring_summary
from authstatus_api.security.password_hashing import verify_password
from authstatus_api.security.password_policy import (
    PasswordPolicyError,
    validate_password_policy,
)
from authstatus_api.security.schemas import (
    AdminMfaResetResponse,
    AdminPasswordResetResponse,
    AdminUserCreateResponse,
    AuditEventListResponse,
    AuditEventResponse,
    AuditIntegrityResponse,
    ChangePasswordRequest,
    CurrentUserResponse,
    InitialAdminSetupRequest,
    InitialAdminSetupResponse,
    InitialAdminSetupStatusResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    MfaEnrollmentConfirmRequest,
    MfaEnrollmentConfirmResponse,
    MfaEnrollmentStartRequest,
    MfaEnrollmentStartResponse,
    MfaLoginVerifyRequest,
    MfaStatusResponse,
    PasswordUpdateResponse,
    SecurityMonitoringSummaryResponse,
    SessionResponse,
    TrustedDeviceRevokeResponse,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
    WalkthroughStatusResponse,
    WalkthroughStepUpdateRequest,
)
from authstatus_api.security.sessions import (
    get_active_session_by_token,
    renew_session,
    replace_user_session,
    revoke_session,
    revoke_user_sessions,
)
from authstatus_api.security.temporary_passwords import (
    generate_temporary_password,
)
from authstatus_api.security.trusted_devices import (
    DEFAULT_TRUSTED_DEVICE_DAYS,
    create_trusted_device,
    get_active_trusted_device_by_token,
    revoke_user_trusted_devices,
    touch_trusted_device,
)
from authstatus_api.security.users import (
    UserLockedError,
    authenticate_user,
    create_user,
    get_user_by_id,
    get_user_for_session_token,
    list_users,
    update_user,
    update_user_password,
    update_user_walkthrough_status,
    update_user_walkthrough_step,
    user_exists,
)
from authstatus_api.settings import get_settings

REQUIRE_CREDENTIAL_ROTATION = True

router = APIRouter(prefix="/api/security", tags=["security"])

AdminUserDependency = Depends(require_role("Admin"))


def _client_ip(request: Request) -> str:
    if request.client is None:
        return ""

    return request.client.host


def _is_loopback_client(request: Request) -> bool:
    if request.client is None:
        return False

    try:
        return ip_address(request.client.host).is_loopback
    except ValueError:
        return False


def _require_loopback_initial_setup(request: Request) -> None:
    if _is_loopback_client(request):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Initial admin setup must be completed from the local machine.",
    )


def _user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=user["id"],
        username=user["username"],
        role=user["role"],
        is_active=user["is_active"],
        last_login_at=user["last_login_at"],
        password_changed_at=user["password_changed_at"],
        must_change_password=user["must_change_password"],
        mfa_enabled=user["mfa_enabled"],
        walkthrough_status=user["walkthrough_status"],
        walkthrough_step=user["walkthrough_step"],
    )


@router.get(
    "/setup-initial-admin/status",
    response_model=InitialAdminSetupStatusResponse,
)
def get_initial_admin_setup_status(
    request: Request,
) -> InitialAdminSetupStatusResponse:
    _require_loopback_initial_setup(request)

    return InitialAdminSetupStatusResponse(
        setup_available=not user_exists(),
    )


@router.post(
    "/setup-initial-admin",
    response_model=InitialAdminSetupResponse,
    status_code=status.HTTP_201_CREATED,
)
def setup_initial_admin(
    payload: InitialAdminSetupRequest,
    request: Request,
) -> InitialAdminSetupResponse:
    _require_loopback_initial_setup(request)

    if user_exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Initial admin setup is no longer available.",
        )

    try:
        validate_password_policy(payload.password)
    except PasswordPolicyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None

    try:
        user = create_user(
            payload.username,
            payload.password,
            role="Admin",
            must_change_password=False,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Initial admin setup is no longer available.",
        ) from None

    record_audit_event(
        action="security.initial_admin_setup",
        resource_type="user",
        resource_id=user["id"],
        user=user,
        metadata={"role": "Admin"},
        request=request,
    )

    return InitialAdminSetupResponse(
        user=_user_response(user),
        setup_complete=True,
    )


@router.get("/users", response_model=UserListResponse)
def read_users(current_user: dict = AdminUserDependency) -> UserListResponse:
    return UserListResponse(
        users=[_user_response(user) for user in list_users()],
    )


@router.get("/audit-events", response_model=AuditEventListResponse)
def read_audit_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None),
    username: str | None = Query(default=None),
    current_user: dict = AdminUserDependency,
) -> AuditEventListResponse:
    result = list_audit_events(
        page=page,
        page_size=page_size,
        action=action,
        username=username,
    )

    return AuditEventListResponse(
        events=[AuditEventResponse(**event) for event in result["events"]],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
    )


@router.post(
    "/audit-events/verify-integrity",
    response_model=AuditIntegrityResponse,
)
def verify_audit_integrity(
    request: Request,
    current_user: dict = AdminUserDependency,
) -> AuditIntegrityResponse:
    result = verify_audit_chain()

    try:
        record_audit_event(
            action="security.audit_integrity_verified",
            resource_type="audit_log",
            user=current_user,
            metadata={
                "valid": result["valid"],
                "status": result["status"],
                "checked_events": result["checked_events"],
                "legacy_events": result["legacy_events"],
                "failed_event_id": result["failed_event_id"],
            },
            request=request,
        )
    except RuntimeError:
        pass

    return AuditIntegrityResponse(**result)


@router.get(
    "/monitoring/summary",
    response_model=SecurityMonitoringSummaryResponse,
)
def read_security_monitoring_summary(
    hours: int = Query(default=24, ge=1, le=168),
    current_user: dict = AdminUserDependency,
) -> SecurityMonitoringSummaryResponse:
    del current_user

    result = get_security_monitoring_summary(hours=hours)

    return SecurityMonitoringSummaryResponse(**result)


@router.post(
    "/users",
    response_model=AdminUserCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_managed_user(
    payload: UserCreateRequest,
    request: Request,
    current_user: dict = AdminUserDependency,
) -> AdminUserCreateResponse:
    temporary_password = generate_temporary_password()

    user = create_user(
        payload.username,
        temporary_password,
        role=payload.role,
        must_change_password=True,
    )

    record_audit_event(
        action="user.create",
        resource_type="user",
        resource_id=user["id"],
        user=current_user,
        metadata={
            "role": payload.role,
            "must_change_password": REQUIRE_CREDENTIAL_ROTATION,
        },
        request=request,
    )

    return AdminUserCreateResponse(
        user=_user_response(user),
        temporary_password=temporary_password,
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_managed_user(
    user_id: int,
    payload: UserUpdateRequest,
    request: Request,
    current_user: dict = AdminUserDependency,
) -> UserResponse:
    payload_data = payload.model_dump(exclude_unset=True)
    target_user = get_user_by_id(user_id)

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not payload_data:
        user = update_user(user_id)
    else:
        if user_id == current_user["id"] and (
            "role" in payload_data or payload_data.get("is_active") is False
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admins cannot remove their own admin access.",
            )

        user = update_user(
            user_id,
            role=payload_data.get("role"),
            is_active=payload_data.get("is_active"),
        )

    role_changed = user["role"] != target_user["role"]
    account_disabled = target_user["is_active"] and not user["is_active"]

    sessions_revoked = 0
    trusted_devices_revoked = 0

    if role_changed or account_disabled:
        sessions_revoked = revoke_user_sessions(user_id)
        trusted_devices_revoked = revoke_user_trusted_devices(user_id)

    record_audit_event(
        action="user.update",
        resource_type="user",
        resource_id=user_id,
        user=current_user,
        metadata={
            "fields": sorted(payload_data.keys()),
            "sessions_revoked": sessions_revoked,
            "trusted_devices_revoked": trusted_devices_revoked,
        },
        request=request,
    )

    return _user_response(user)


@router.post(
    "/change-password",
    response_model=PasswordUpdateResponse,
)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: dict = AuthenticatedUserDependency,
) -> PasswordUpdateResponse:
    if not verify_password(
        current_user["password_hash"],
        payload.current_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )

    try:
        validate_password_policy(payload.new_password)
    except PasswordPolicyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None

    updated_user = update_user_password(
        current_user["id"],
        new_password=payload.new_password,
        must_change_password=False,
    )

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    sessions_revoked = revoke_user_sessions(current_user["id"])
    trusted_devices_revoked = revoke_user_trusted_devices(current_user["id"])

    record_audit_event(
        action="security.password_change",
        resource_type="user",
        resource_id=current_user["id"],
        user=current_user,
        metadata={
            "sessions_revoked": sessions_revoked,
            "trusted_devices_revoked": trusted_devices_revoked,
        },
        request=request,
    )

    return PasswordUpdateResponse(
        password_changed=True,
        sessions_revoked=sessions_revoked,
    )


@router.get(
    "/mfa/status",
    response_model=MfaStatusResponse,
)
def get_mfa_status(
    current_user: dict = CurrentUserDependency,
) -> MfaStatusResponse:
    secret = get_user_mfa_secret(current_user["id"])

    return MfaStatusResponse(
        enabled=current_user["mfa_enabled"],
        enrollment_pending=bool(secret) and not current_user["mfa_enabled"],
    )


@router.delete(
    "/mfa/trusted-devices",
    response_model=TrustedDeviceRevokeResponse,
)
def revoke_current_user_trusted_devices(
    request: Request,
    response: Response,
    current_user: dict = CurrentUserDependency,
) -> TrustedDeviceRevokeResponse:
    trusted_devices_revoked = revoke_user_trusted_devices(current_user["id"])
    settings = get_settings()

    response.delete_cookie(
        key=settings.trusted_device_cookie_name,
        path="/api/security/login",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )

    record_audit_event(
        action="security.trusted_devices_revoked",
        resource_type="user",
        resource_id=current_user["id"],
        user=current_user,
        metadata={
            "trusted_devices_revoked": trusted_devices_revoked,
        },
        request=request,
    )

    return TrustedDeviceRevokeResponse(
        trusted_devices_revoked=trusted_devices_revoked,
    )


@router.post(
    "/mfa/enroll",
    response_model=MfaEnrollmentStartResponse,
)
def start_mfa_enrollment(
    payload: MfaEnrollmentStartRequest,
    request: Request,
    current_user: dict = CurrentUserDependency,
) -> MfaEnrollmentStartResponse:
    if current_user["mfa_enabled"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MFA is already enabled.",
        )

    if not verify_password(
        current_user["password_hash"],
        payload.current_password,
    ):
        record_audit_event(
            action="security.mfa_enrollment_password_failed",
            resource_type="user",
            resource_id=current_user["id"],
            user=current_user,
            request=request,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    secret = generate_totp_secret()

    if not store_user_mfa_secret(current_user["id"], secret):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    provisioning_uri = build_totp_provisioning_uri(
        current_user["username"],
        secret,
    )

    record_audit_event(
        action="security.mfa_enrollment_started",
        resource_type="user",
        resource_id=current_user["id"],
        user=current_user,
        request=request,
    )

    return MfaEnrollmentStartResponse(
        secret=secret,
        provisioning_uri=provisioning_uri,
    )


@router.post(
    "/mfa/enroll/confirm",
    response_model=MfaEnrollmentConfirmResponse,
)
def confirm_mfa_enrollment(
    payload: MfaEnrollmentConfirmRequest,
    request: Request,
    current_user: dict = CurrentUserDependency,
) -> MfaEnrollmentConfirmResponse:
    if current_user["mfa_enabled"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MFA is already enabled.",
        )

    secret = get_user_mfa_secret(current_user["id"])

    if secret is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MFA enrollment has not been started.",
        )

    if not verify_totp_code(secret, payload.code):
        record_audit_event(
            action="security.mfa_enrollment_verification_failed",
            resource_type="user",
            resource_id=current_user["id"],
            user=current_user,
            request=request,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authentication code.",
        )

    if not enable_user_mfa(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to enable MFA.",
        )

    record_audit_event(
        action="security.mfa_enabled",
        resource_type="user",
        resource_id=current_user["id"],
        user=current_user,
        request=request,
    )

    return MfaEnrollmentConfirmResponse(
        enabled=True,
    )


@router.post(
    "/users/{user_id}/reset-password",
    response_model=AdminPasswordResetResponse,
)
def reset_managed_user_password(
    user_id: int,
    request: Request,
    current_user: dict = AdminUserDependency,
) -> AdminPasswordResetResponse:
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use change password to update your own password.",
        )

    target_user = get_user_by_id(user_id)

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    temporary_password = generate_temporary_password()

    updated_user = update_user_password(
        user_id,
        new_password=temporary_password,
        must_change_password=True,
    )

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    sessions_revoked = revoke_user_sessions(user_id)
    trusted_devices_revoked = revoke_user_trusted_devices(user_id)

    record_audit_event(
        action="user.password_reset",
        resource_type="user",
        resource_id=user_id,
        user=current_user,
        metadata={
            "sessions_revoked": sessions_revoked,
            "trusted_devices_revoked": trusted_devices_revoked,
            "must_change_password": REQUIRE_CREDENTIAL_ROTATION,
        },
        request=request,
    )

    return AdminPasswordResetResponse(
        password_reset=True,
        temporary_password=temporary_password,
        sessions_revoked=sessions_revoked,
        must_change_password=True,
    )


@router.post(
    "/users/{user_id}/reset-mfa",
    response_model=AdminMfaResetResponse,
)
def reset_managed_user_mfa(
    user_id: int,
    request: Request,
    current_user: dict = AdminUserDependency,
) -> AdminMfaResetResponse:
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot reset their own MFA from user management.",
        )

    target_user = get_user_by_id(user_id)

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not clear_user_mfa(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    sessions_revoked = revoke_user_sessions(user_id)
    trusted_devices_revoked = revoke_user_trusted_devices(user_id)

    record_audit_event(
        action="user.mfa_reset",
        resource_type="user",
        resource_id=user_id,
        user=current_user,
        metadata={
            "sessions_revoked": sessions_revoked,
            "trusted_devices_revoked": trusted_devices_revoked,
        },
        request=request,
    )

    return AdminMfaResetResponse(
        mfa_reset=True,
        sessions_revoked=sessions_revoked,
        mfa_enabled=False,
    )


@router.post(
    "/users/{user_id}/walkthrough/restart",
    response_model=WalkthroughStatusResponse,
)
def restart_managed_user_walkthrough(
    user_id: int,
    request: Request,
    current_user: dict = AdminUserDependency,
) -> WalkthroughStatusResponse:
    target_user = get_user_by_id(user_id)

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    updated_user = update_user_walkthrough_status(
        user_id,
        "pending",
    )

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    updated_user = update_user_walkthrough_step(
        user_id,
        None,
    )

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    record_audit_event(
        action="walkthrough.restart",
        resource_type="user",
        resource_id=user_id,
        user=current_user,
        metadata={
            "previous_status": target_user["walkthrough_status"],
        },
        request=request,
    )

    return WalkthroughStatusResponse(
        walkthrough_status=updated_user["walkthrough_status"],
        walkthrough_step=updated_user["walkthrough_step"],
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    response_model_exclude_defaults=True,
    response_model_exclude_none=True,
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
) -> LoginResponse:
    try:
        user = authenticate_user(payload.username, payload.password)
    except UserLockedError:
        record_audit_event(
            action="security.login_locked",
            resource_type="security",
            metadata={"username": payload.username.strip().lower()},
            request=request,
            username=payload.username.strip().lower(),
        )

        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked. Try again later.",
        ) from None

    if user is None:
        record_audit_event(
            action="security.login_failed",
            resource_type="security",
            metadata={"username": payload.username.strip().lower()},
            request=request,
            username=payload.username.strip().lower(),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    if user["mfa_enabled"]:
        settings = get_settings()
        trusted_device_token = request.cookies.get(settings.trusted_device_cookie_name)

        if trusted_device_token:
            trusted_device = get_active_trusted_device_by_token(trusted_device_token)

            if (
                trusted_device is not None
                and trusted_device["user_id"] == user["id"]
                and touch_trusted_device(trusted_device_token)
            ):
                record_audit_event(
                    action="security.login_trusted_device",
                    resource_type="trusted_device",
                    resource_id=trusted_device["id"],
                    user=user,
                    metadata={
                        "expires_at": trusted_device["expires_at"],
                    },
                    request=request,
                )

                return _create_authenticated_session_response(
                    user=user,
                    request=request,
                    response=response,
                )

        created_challenge = create_mfa_login_challenge(
            user["id"],
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        challenge = created_challenge["challenge"]

        response.delete_cookie(
            key=settings.session_cookie_name,
            path="/api",
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite="lax",
        )

        response.delete_cookie(
            key=settings.csrf_cookie_name,
            path="/",
            httponly=False,
            secure=settings.session_cookie_secure,
            samesite="lax",
        )

        record_audit_event(
            action="security.login_mfa_required",
            resource_type="mfa_login_challenge",
            resource_id=challenge["id"],
            user=user,
            request=request,
        )

        return LoginResponse(
            mfa_required=True,
            mfa_challenge_token=created_challenge["token"],
            expires_at=challenge["expires_at"],
        )

    return _create_authenticated_session_response(
        user=user,
        request=request,
        response=response,
    )


def _create_authenticated_session_response(
    *,
    user: dict,
    request: Request,
    response: Response,
) -> LoginResponse:
    created_session = replace_user_session(
        user["id"],
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )

    session = created_session["session"]
    settings = get_settings()
    csrf_token = generate_csrf_token()

    response.set_cookie(
        key=settings.session_cookie_name,
        value=created_session["token"],
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/api",
    )

    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )

    record_audit_event(
        action="security.login",
        resource_type="session",
        resource_id=session["id"],
        user=user,
        metadata={
            "sessions_revoked": created_session["sessions_revoked"],
        },
        request=request,
    )

    return LoginResponse(
        user=_user_response(user),
        session=SessionResponse(
            expires_at=session["expires_at"],
        ),
    )


@router.post(
    "/login/mfa/verify",
    response_model=LoginResponse,
    response_model_exclude_defaults=True,
    response_model_exclude_none=True,
)
def verify_mfa_login(
    payload: MfaLoginVerifyRequest,
    request: Request,
    response: Response,
) -> LoginResponse:
    challenge = get_active_mfa_login_challenge_by_token(
        payload.challenge_token,
    )

    if challenge is None:
        record_audit_event(
            action="security.login_mfa_challenge_invalid",
            resource_type="mfa_login_challenge",
            request=request,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA challenge.",
        )

    user = get_user_by_id(challenge["user_id"])

    if user is None or not user["is_active"] or not user["mfa_enabled"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA challenge.",
        )

    secret = get_user_mfa_secret(user["id"])

    if secret is None or not verify_totp_code(secret, payload.code):
        record_audit_event(
            action="security.login_mfa_failed",
            resource_type="mfa_login_challenge",
            resource_id=challenge["id"],
            user=user,
            request=request,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication code.",
        )

    if not consume_mfa_login_challenge(payload.challenge_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA challenge.",
        )

    record_audit_event(
        action="security.login_mfa_verified",
        resource_type="mfa_login_challenge",
        resource_id=challenge["id"],
        user=user,
        request=request,
    )

    if payload.remember_device:
        trusted_device = create_trusted_device(
            user["id"],
            days=DEFAULT_TRUSTED_DEVICE_DAYS,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        settings = get_settings()

        response.set_cookie(
            key=settings.trusted_device_cookie_name,
            value=trusted_device["token"],
            max_age=DEFAULT_TRUSTED_DEVICE_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite="lax",
            path="/api/security/login",
        )

        record_audit_event(
            action="security.trusted_device_created",
            resource_type="trusted_device",
            resource_id=trusted_device["trusted_device"]["id"],
            user=user,
            metadata={
                "expires_at": trusted_device["trusted_device"]["expires_at"],
            },
            request=request,
        )

    return _create_authenticated_session_response(
        user=user,
        request=request,
        response=response,
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
) -> LogoutResponse:
    settings = get_settings()
    token = extract_session_token(request)
    user = get_user_for_session_token(token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    validate_csrf_request(request)

    logged_out = revoke_session(token)

    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/api",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )

    response.delete_cookie(
        key=settings.csrf_cookie_name,
        path="/",
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )

    if logged_out:
        record_audit_event(
            action="security.logout",
            resource_type="session",
            user=user,
            request=request,
        )

    return LogoutResponse(logged_out=logged_out)


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(
    request: Request,
    user: dict = AuthenticatedUserDependency,
) -> CurrentUserResponse:
    token = extract_session_token(request)
    session = get_active_session_by_token(token)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return CurrentUserResponse(
        user=_user_response(user),
        session=SessionResponse(
            expires_at=session["expires_at"],
        ),
    )


@router.put(
    "/walkthrough/step",
    response_model=WalkthroughStatusResponse,
)
def update_walkthrough_step(
    payload: WalkthroughStepUpdateRequest,
    current_user: dict = CurrentUserDependency,
) -> WalkthroughStatusResponse:
    updated_user = update_user_walkthrough_step(
        current_user["id"],
        payload.walkthrough_step,
    )

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return WalkthroughStatusResponse(
        walkthrough_status=updated_user["walkthrough_status"],
        walkthrough_step=updated_user["walkthrough_step"],
    )


@router.post(
    "/walkthrough/complete",
    response_model=WalkthroughStatusResponse,
)
def complete_walkthrough(
    request: Request,
    current_user: dict = CurrentUserDependency,
) -> WalkthroughStatusResponse:
    updated_user = update_user_walkthrough_status(
        current_user["id"],
        "completed",
    )

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    updated_user = update_user_walkthrough_step(
        current_user["id"],
        None,
    )

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    record_audit_event(
        action="walkthrough.complete",
        resource_type="user",
        resource_id=current_user["id"],
        user=current_user,
        request=request,
    )

    return WalkthroughStatusResponse(
        walkthrough_status=updated_user["walkthrough_status"],
        walkthrough_step=updated_user["walkthrough_step"],
    )


@router.post(
    "/walkthrough/skip",
    response_model=WalkthroughStatusResponse,
)
def skip_walkthrough(
    request: Request,
    current_user: dict = CurrentUserDependency,
) -> WalkthroughStatusResponse:
    updated_user = update_user_walkthrough_status(
        current_user["id"],
        "skipped",
    )

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    updated_user = update_user_walkthrough_step(
        current_user["id"],
        None,
    )

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    record_audit_event(
        action="walkthrough.skip",
        resource_type="user",
        resource_id=current_user["id"],
        user=current_user,
        request=request,
    )

    return WalkthroughStatusResponse(
        walkthrough_status=updated_user["walkthrough_status"],
        walkthrough_step=updated_user["walkthrough_step"],
    )


@router.post(
    "/session/activity",
    response_model=SessionResponse,
)
def record_session_activity(
    request: Request,
    user: dict = AuthenticatedUserDependency,
) -> SessionResponse:
    token = extract_session_token(request)
    session = get_active_session_by_token(token)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return SessionResponse(
        expires_at=session["expires_at"],
    )


@router.post(
    "/session/renew",
    response_model=SessionResponse,
)
def renew_current_session(
    request: Request,
    response: Response,
    user: dict = AuthenticatedUserDependency,
) -> SessionResponse:
    token = extract_session_token(request)
    renewed_session = renew_session(token)

    if renewed_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    settings = get_settings()
    csrf_token = generate_csrf_token()
    session = renewed_session["session"]

    response.set_cookie(
        key=settings.session_cookie_name,
        value=renewed_session["token"],
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/api",
    )

    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )

    return SessionResponse(
        expires_at=session["expires_at"],
    )
