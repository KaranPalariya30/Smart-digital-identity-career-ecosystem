"""The resume service must accept tokens exactly as auth-service signs them."""
import time
from dataclasses import replace

import jwt
import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.config import settings
from app.main import app

SECRET = "shared-secret-that-is-at-least-32-characters"
ROLE_URL = "/api/v1/roles"
ANALYZE_BODY = {"resume_text": "Python developer with FastAPI and SQL experience. " * 4,
                "target_role": None, "mode": "auto"}


def token(purpose="access", secret=SECRET, exp_in=3600, **extra):
    claims = {"sub": "7", "role": "STUDENT", "token_version": 0, "purpose": purpose,
              "exp": int(time.time()) + exp_in, **extra}
    return {"Authorization": "Bearer " + jwt.encode(claims, secret, algorithm="HS256")}


@pytest.fixture()
def secured(monkeypatch):
    monkeypatch.setattr(auth_module, "settings", replace(settings, auth_enabled=True, jwt_secret=SECRET))
    with TestClient(app) as c:
        yield c


def test_requests_without_a_token_are_rejected(secured):
    assert secured.get(ROLE_URL).status_code == 401
    assert secured.post("/api/v1/analyze/text", json=ANALYZE_BODY).status_code == 401


def test_legacy_route_is_not_a_bypass(secured):
    assert secured.post("/analyze", json={"resume_text": "python", "jd_text": "x" * 80}).status_code == 401


def test_access_token_signed_like_auth_service_is_accepted(secured):
    assert secured.get(ROLE_URL, headers=token()).status_code == 200


@pytest.mark.parametrize("headers", [
    token(secret="y" * 40),               # wrong key
    token(exp_in=-5),                     # expired
    token(purpose="password_reset"),      # other auth-service token type
    {"Authorization": "Bearer junk"},
])
def test_bad_tokens_are_rejected(secured, headers):
    assert secured.get(ROLE_URL, headers=headers).status_code == 401


def test_auth_on_without_a_secret_fails_closed(monkeypatch):
    monkeypatch.setattr(auth_module, "settings", replace(settings, auth_enabled=True, jwt_secret=""))
    with TestClient(app) as c:
        assert c.get(ROLE_URL, headers=token()).status_code == 503


def test_verified_skills_are_flagged_in_the_analysis(secured):
    body = {**ANALYZE_BODY, "target_role": "backend_python", "verified_skills": ["Python"]}
    r = secured.post("/api/v1/analyze/text", json=body, headers=token())
    assert r.status_code == 200, r.text
    skills = r.json()["skills"]
    python = next(s for s in skills["matched"] if s["name"] == "python")
    assert python["verified"] is True
    assert skills["verified_percentage"] > 0
