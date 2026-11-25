from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.database.models import User
from app.main import app
from scripts.create_user import upsert_user


def test_cors_allows_the_frontend_origin_only():
    client = TestClient(app)
    ok = client.options(
        "/api/auth/login",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
                 "Access-Control-Request-Headers": "content-type"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options(
        "/api/auth/login",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in bad.headers


def _db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_create_user_makes_a_verified_admin():
    db = _db()
    u = upsert_user(db, name="Demo Admin", email="admin@example.com", password="Admin@12345", role="admin")
    assert (u.role, u.is_verified, u.is_active) == ("ADMIN", True, True)


def test_create_user_promotes_existing_user_and_signs_out_old_sessions():
    db = _db()
    first = upsert_user(db, name="S", email="s@example.com", password="Student@123", role="STUDENT")
    before = first.token_version
    again = upsert_user(db, name="S", email="s@example.com", password="Student@123", role="ADMIN")
    assert again.id == first.id and again.role == "ADMIN" and again.token_version == before + 1
    assert db.query(User).count() == 1


def test_create_user_rejects_bad_input():
    db = _db()
    for kwargs in ({"role": "ROOT", "password": "Password123"}, {"role": "ADMIN", "password": "short"}):
        try:
            upsert_user(db, name="x", email="x@example.com", **kwargs)
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_create_user_rejects_emails_the_login_form_would_refuse():
    db = _db()
    try:
        upsert_user(db, name="x", email="admin@demo.local", password="Password123", role="ADMIN")
    except ValueError as exc:
        assert "invalid email" in str(exc)
    else:
        raise AssertionError("expected ValueError")
