"""Authorization for the credential API.

Two kinds of caller can issue or revoke credentials:

* a logged-in user whose auth-service JWT carries an issuer role (ADMIN by
  default) - this is what the web app uses, and
* a script or backend that presents the static SERVICE_API_TOKEN.

Anyone with a valid JWT (any role) can read their own credentials.
Verification stays public by design.
"""
import secrets
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    kind: str                      # "user" or "service"
    user_id: str | None = None
    role: str | None = None


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _token_from(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Missing authentication token")
    return credentials.credentials


def _is_service_token(token: str) -> bool:
    expected = get_settings().service_api_token
    return bool(expected) and secrets.compare_digest(token.encode(), expected.encode())


def _decode_user_token(token: str) -> dict | None:
    """Verify an auth-service access token. Returns the claims or None."""
    settings = get_settings()
    if not settings.auth_secret_key:
        return None
    try:
        claims = jwt.decode(token, settings.auth_secret_key, algorithms=[settings.auth_algorithm])
    except jwt.PyJWTError:
        return None
    # auth-service also signs email-verification and password-reset tokens
    # with the same key; only "access" tokens may be used here.
    if claims.get("purpose") != "access" or not claims.get("sub"):
        return None
    return claims


def _ensure_configured() -> None:
    settings = get_settings()
    if not settings.auth_secret_key and not settings.service_api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured (set AUTH_SECRET_KEY and/or SERVICE_API_TOKEN)",
        )


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    """Any logged-in user."""
    _ensure_configured()
    claims = _decode_user_token(_token_from(credentials))
    if claims is None:
        raise _unauthorized("Invalid or expired token")
    return Principal("user", user_id=str(claims["sub"]), role=str(claims.get("role", "")).upper())


def require_issuer(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    """A user with an issuer role, or the static service token."""
    _ensure_configured()
    token = _token_from(credentials)

    if _is_service_token(token):
        return Principal("service")

    claims = _decode_user_token(token)
    if claims is None:
        raise _unauthorized("Invalid or expired token")

    role = str(claims.get("role", "")).upper()
    if role not in get_settings().issuer_role_set:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an issuer can perform this action",
        )
    return Principal("user", user_id=str(claims["sub"]), role=role)
