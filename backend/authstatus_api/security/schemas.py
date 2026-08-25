from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr

UserRole = Literal["Admin", "UR", "Read Only"]

WalkthroughStatus = Literal["pending", "completed", "skipped"]


class LoginRequest(BaseModel):
    username: str
    password: str

    model_config = ConfigDict(extra="forbid")


class UserCreateRequest(BaseModel):
    username: EmailStr
    role: UserRole = "UR"

    model_config = ConfigDict(extra="forbid")


class UserUpdateRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class InitialAdminSetupRequest(BaseModel):
    username: EmailStr
    password: str

    model_config = ConfigDict(extra="forbid")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    model_config = ConfigDict(extra="forbid")


class MfaEnrollmentStartRequest(BaseModel):
    current_password: str

    model_config = ConfigDict(extra="forbid")


class MfaEnrollmentStartResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MfaEnrollmentConfirmRequest(BaseModel):
    code: str

    model_config = ConfigDict(extra="forbid")


class MfaEnrollmentConfirmResponse(BaseModel):
    enabled: bool


class MfaStatusResponse(BaseModel):
    enabled: bool
    enrollment_pending: bool


class TrustedDeviceRevokeResponse(BaseModel):
    trusted_devices_revoked: int


class WalkthroughStatusResponse(BaseModel):
    walkthrough_status: WalkthroughStatus


class MfaLoginVerifyRequest(BaseModel):
    challenge_token: str
    code: str
    remember_device: bool = False

    model_config = ConfigDict(extra="forbid")


class PasswordUpdateResponse(BaseModel):
    password_changed: bool
    sessions_revoked: int


class AdminPasswordResetResponse(BaseModel):
    password_reset: bool
    temporary_password: str
    sessions_revoked: int
    must_change_password: bool


class AdminMfaResetResponse(BaseModel):
    mfa_reset: bool
    sessions_revoked: int
    mfa_enabled: bool


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    last_login_at: str | None = None
    password_changed_at: str
    must_change_password: bool
    mfa_enabled: bool
    walkthrough_status: WalkthroughStatus


class AdminUserCreateResponse(BaseModel):
    user: UserResponse
    temporary_password: str


class InitialAdminSetupResponse(BaseModel):
    user: UserResponse
    setup_complete: bool


class InitialAdminSetupStatusResponse(BaseModel):
    setup_available: bool


class UserListResponse(BaseModel):
    users: list[UserResponse]


class SessionResponse(BaseModel):
    expires_at: str


class LoginResponse(BaseModel):
    user: UserResponse | None = None
    session: SessionResponse | None = None
    mfa_required: bool = False
    mfa_challenge_token: str | None = None
    expires_at: str | None = None


class CurrentUserResponse(BaseModel):
    user: UserResponse
    session: SessionResponse


class LogoutResponse(BaseModel):
    logged_out: bool


class AuditEventResponse(BaseModel):
    id: int
    user_id: int | None = None
    username: str | None = None
    action: str
    resource_type: str
    resource_id: int | None = None
    metadata: str
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: str


class AuditEventListResponse(BaseModel):
    events: list[AuditEventResponse]
    page: int
    page_size: int
    total: int


class AuditIntegrityResponse(BaseModel):
    valid: bool
    status: Literal["valid", "invalid", "not_initialized"]
    checked_events: int
    legacy_events: int
    failed_event_id: int | None = None
    reason: str | None = None


class SecurityMonitoringSummaryResponse(BaseModel):
    window_hours: int
    failed_logins: int
    locked_logins: int
    failed_mfa: int
    total_failures: int
    distinct_failure_ips: int
    distinct_failure_usernames: int
    max_failures_single_username: int
    max_failures_single_ip: int
    severity: Literal["normal", "elevated", "high"]
