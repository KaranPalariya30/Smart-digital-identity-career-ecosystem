import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.routes import auth as auth_routes


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(auth_routes.router)
    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(
        auth_routes,
        "EMAIL_VERIFICATION_DEV_MODE",
        True
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_complete_authentication_flow(client):
    # 1. Register
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test Student",
            "email": "teststudent@example.com",
            "password": "OldPassword123!"
        }
    )

    assert response.status_code == 201
    registration = response.json()
    verification_token = registration["verification_token"]

    # 2. Login before email verification must fail
    response = client.post(
        "/api/auth/login",
        json={
            "email": "teststudent@example.com",
            "password": "OldPassword123!"
        }
    )

    assert response.status_code == 403

    # 3. Verify email
    response = client.post(
        "/api/auth/verify-email",
        json={"token": verification_token}
    )

    assert response.status_code == 200

    # 4. Login
    response = client.post(
        "/api/auth/login",
        json={
            "email": "teststudent@example.com",
            "password": "OldPassword123!"
        }
    )

    assert response.status_code == 200
    old_access_token = response.json()["access_token"]

    # 5. Access protected profile
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {old_access_token}"}
    )

    assert response.status_code == 200

    # 6. Request password reset
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": "teststudent@example.com"}
    )

    assert response.status_code == 200
    reset_token = response.json()["reset_token"]

    # 7. Reset password
    response = client.post(
        "/api/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "NewPassword456!"
        }
    )

    assert response.status_code == 200

    # 8. Old access token must be rejected
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {old_access_token}"}
    )

    assert response.status_code == 401

    # 9. Reusing the reset token must fail
    response = client.post(
        "/api/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "AnotherPassword789!"
        }
    )

    assert response.status_code == 400

    # 10. Old password must fail
    response = client.post(
        "/api/auth/login",
        json={
            "email": "teststudent@example.com",
            "password": "OldPassword123!"
        }
    )

    assert response.status_code == 401

    # 11. New password must work
    response = client.post(
        "/api/auth/login",
        json={
            "email": "teststudent@example.com",
            "password": "NewPassword456!"
        }
    )

    assert response.status_code == 200

    print("PASS: Complete authentication flow")


def test_token_purpose_validation(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Purpose Test",
            "email": "purpose@example.com",
            "password": "TestPassword123!"
        }
    )

    verification_token = response.json()["verification_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {verification_token}"}
    )

    assert response.status_code == 401

    print("PASS: Email verification token rejected as access token")


def test_production_email_delivery(client, monkeypatch):
    sent_emails = []

    monkeypatch.setattr(
        auth_routes,
        "EMAIL_VERIFICATION_DEV_MODE",
        False
    )

    monkeypatch.setattr(
        auth_routes,
        "FRONTEND_VERIFY_BASE_URL",
        "https://frontend.example/verify-email"
    )

    monkeypatch.setattr(
        auth_routes,
        "FRONTEND_RESET_PASSWORD_BASE_URL",
        "https://frontend.example/reset-password"
    )

    monkeypatch.setattr(
        auth_routes,
        "send_auth_email",
        lambda **kwargs: sent_emails.append(kwargs)
    )

    # 1. Register user
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Production Test",
            "email": "production@example.com",
            "password": "TestPassword123!"
        }
    )

    assert response.status_code == 201
    assert "verification_token" not in response.json()
    assert len(sent_emails) == 1

    assert sent_emails[0]["to_email"] == "production@example.com"
    assert "https://frontend.example/verify-email?token=" in sent_emails[0]["body"]

    # 2. Request password reset
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": "production@example.com"}
    )

    assert response.status_code == 200
    assert "reset_token" not in response.json()
    assert len(sent_emails) == 2

    assert sent_emails[1]["to_email"] == "production@example.com"
    assert "https://frontend.example/reset-password?token=" in sent_emails[1]["body"]

    print("PASS: Production email workflows")


def test_registration_email_failure_cleanup(client, monkeypatch):
    monkeypatch.setattr(
        auth_routes,
        "EMAIL_VERIFICATION_DEV_MODE",
        False
    )

    def failing_email_sender(**kwargs):
        raise RuntimeError("Simulated SMTP failure")

    monkeypatch.setattr(
        auth_routes,
        "send_auth_email",
        failing_email_sender
    )

    user_data = {
        "name": "Email Failure Test",
        "email": "emailfailure@example.com",
        "password": "TestPassword123!"
    }

    # Registration should fail when the email cannot be sent.
    response = client.post(
        "/api/auth/register",
        json=user_data
    )

    assert response.status_code == 503

    # Retry in development mode. This should succeed only if
    # the previous incomplete account was deleted.
    monkeypatch.setattr(
        auth_routes,
        "EMAIL_VERIFICATION_DEV_MODE",
        True
    )

    response = client.post(
        "/api/auth/register",
        json=user_data
    )

    assert response.status_code == 201

    print("PASS: Failed email delivery cleans up incomplete registration")


def test_password_reset_email_failure(client, monkeypatch):
    monkeypatch.setattr(
        auth_routes,
        "EMAIL_VERIFICATION_DEV_MODE",
        True
    )

    # Register a user and verify their email.
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Reset Failure Test",
            "email": "resetfailure@example.com",
            "password": "OriginalPassword123!"
        }
    )

    assert response.status_code == 201

    verification_token = response.json()["verification_token"]

    response = client.post(
        "/api/auth/verify-email",
        json={"token": verification_token}
    )

    assert response.status_code == 200

    # Switch to production email mode.
    monkeypatch.setattr(
        auth_routes,
        "EMAIL_VERIFICATION_DEV_MODE",
        False
    )

    def failing_email_sender(**kwargs):
        raise RuntimeError("Simulated SMTP failure")

    monkeypatch.setattr(
        auth_routes,
        "send_auth_email",
        failing_email_sender
    )

    # Password reset request should return 503.
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": "resetfailure@example.com"}
    )

    assert response.status_code == 503

    # Original password must still work.
    monkeypatch.setattr(
        auth_routes,
        "EMAIL_VERIFICATION_DEV_MODE",
        True
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "resetfailure@example.com",
            "password": "OriginalPassword123!"
        }
    )

    assert response.status_code == 200

    print("PASS: Password reset email failure handling")
