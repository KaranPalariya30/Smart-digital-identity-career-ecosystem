"""JWT check so this service can sit behind the platform's login.

Off by default (handy for running the service on its own). Turn it on with
AUTH_ENABLED=true and set JWT_SECRET to the SAME value as SECRET_KEY in
backend/auth-service/.env - the auth-service signs the tokens, this service
only verifies them.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def require_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict | None:
    if not settings.auth_enabled:
        return None
    if not settings.jwt_secret:
        # Never verify against an empty key: anyone could sign a token with it.
        raise HTTPException(status_code=503, detail="AUTH_ENABLED is on but JWT_SECRET is not set")
    if creds is None:
        raise _unauthorized("Missing bearer token")
    import jwt  # PyJWT, imported lazily so it is only needed when auth is on
    try:
        claims = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise _unauthorized(f"Invalid token: {exc}") from exc
    # The auth-service signs several kinds of token with one key; only a
    # login ("access") token may call this API.
    if claims.get("purpose", "access") != "access":
        raise _unauthorized("Invalid token purpose")
    return claims
