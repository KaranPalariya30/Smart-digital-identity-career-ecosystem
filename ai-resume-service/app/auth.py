"""Optional JWT check so this service can sit behind the main backend's login.
Off by default. Turn on with AUTH_ENABLED=true and JWT_SECRET=<shared secret>."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

_bearer = HTTPBearer(auto_error=False)


def require_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict | None:
    if not settings.auth_enabled:
        return None
    if creds is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    import jwt  # PyJWT, imported lazily so it is only needed when auth is on
    try:
        return jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
