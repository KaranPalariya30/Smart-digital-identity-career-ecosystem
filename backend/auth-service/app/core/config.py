
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./smart_identity.db"
)

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError(
        "SECRET_KEY must be configured with at least 32 characters."
    )

ALGORITHM = os.getenv("ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

EMAIL_VERIFICATION_DEV_MODE = (
    os.getenv("EMAIL_VERIFICATION_DEV_MODE", "true").lower() == "true"
)

FRONTEND_VERIFY_BASE_URL = os.getenv(
    "FRONTEND_VERIFY_BASE_URL",
    "http://localhost:3000/verify-email"
)

FRONTEND_RESET_PASSWORD_BASE_URL = os.getenv(
    "FRONTEND_RESET_PASSWORD_BASE_URL",
    "http://localhost:3000/reset-password"
)