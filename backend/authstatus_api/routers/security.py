from __future__ import annotations

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
from authstatus_api.security.csrf import (
    generate_csrf_token,
    validate_csrf_request,
)
from authstatus_api.security.dependencies import (
    AuthenticatedUserDependency,
    extract_session_token,
    require_role,
)
from authstatus_api.security.password_hashing import verify_password
from authstatus_api.security.schemas import (
    AdminPasswordResetResponse,
    AdminUserCreateResponse,
    AuditEventListResponse,
    AuditEventResponse,
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    PasswordUpdateResponse,
    SessionResponse,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from authstatus_api.security.sessions import (
    DEFAULT_SESSION_MINUTES,
    create_user_session,
    get_active_session_by_token,
    renew_session,
    revoke_session,
    revoke_user_sessions,
)
from authstatus_api.security.temporary_passwords import (
    generate_temporary_password,
)
from authstatus_api.security.users import (
    authenticate_user,
    create_user,
    get_user_by_id,
    get_user_for_session_token,
    list_users,
    update_user,
    update_user_password,
)
from authstatus_api.settings import get_settings

REQUIRE_CREDENTIAL_ROTATION = True

router = APIRouter(prefix="/api/security", tags=["security"])

AdminUserDependency = Depends(require_role("Admin"))


def _client_ip(request: Request) -> str:
    if request.client is None:
        return ""

    return request.client.host


def _user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=user["id"],
        username=user["username"],
        role=user["role"],
        is_active=user["is_active"],
        last_login_at=user["last_login_at"],
        password_changed_at=user["password_changed_at"],
        must_change_password=user["must_change_password"],
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

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    record_audit_event(
        action="user.update",
        resource_type="user",
        resource_id=user_id,
        user=current_user,
        metadata={"fields": sorted(payload_data.keys())},
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

    record_audit_event(
        action="security.password_change",
        resource_type="user",
        resource_id=current_user["id"],
        user=current_user,
        metadata={"sessions_revoked": sessions_revoked},
        request=request,
    )

    return PasswordUpdateResponse(
        password_changed=True,
        sessions_revoked=sessions_revoked,
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

    record_audit_event(
        action="user.password_reset",
        resource_type="user",
        resource_id=user_id,
        user=current_user,
        metadata={
            "sessions_revoked": sessions_revoked,
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


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
) -> LoginResponse:
    user = authenticate_user(payload.username, payload.password)

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

    created_session = create_user_session(
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
        max_age=DEFAULT_SESSION_MINUTES * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/api",
    )

    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=DEFAULT_SESSION_MINUTES * 60,
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
        request=request,
    )

    return LoginResponse(
        user=_user_response(user),
        session=SessionResponse(
            expires_at=session["expires_at"],
        ),
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
        max_age=DEFAULT_SESSION_MINUTES * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/api",
    )

    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=DEFAULT_SESSION_MINUTES * 60,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )

    return SessionResponse(
        expires_at=session["expires_at"],
    )
