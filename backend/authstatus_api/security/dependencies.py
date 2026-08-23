from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, Response, status

from authstatus_api.governance.repository import (
    is_governance_attestation_current,
)
from authstatus_api.security.csrf import validate_csrf_request
from authstatus_api.security.sessions import touch_session
from authstatus_api.security.users import get_user_for_session_token
from authstatus_api.settings import get_settings


def extract_session_token(request: Request) -> str:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return token


def get_authenticated_user(
    request: Request,
    response: Response,
) -> dict:
    token = extract_session_token(request)
    user = get_user_for_session_token(
        token,
        touch=False,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    validate_csrf_request(request)

    expires_at = touch_session(token)

    if expires_at is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    response.headers["X-CareQueue-Session-Expires-At"] = expires_at

    return user


AuthenticatedUserDependency = Depends(get_authenticated_user)


def get_current_user(
    authenticated_user: dict = AuthenticatedUserDependency,
) -> dict:
    if authenticated_user["must_change_password"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required.",
        )

    if not is_governance_attestation_current():
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Governance attestation required.",
        )

    return authenticated_user


CurrentUserDependency = Depends(get_current_user)


def require_role(*allowed_roles: str) -> Callable:
    def dependency(
        current_user: dict = CurrentUserDependency,
    ) -> dict:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for this role.",
            )

        return current_user

    return dependency
