"""Create or update a user with a given role - already verified, ready to log in.

Registration through the API only ever creates STUDENT accounts, so this is
how an ADMIN (credential issuer) or RECRUITER gets created without writing SQL.

    python scripts/create_user.py --email admin@example.com --password 'Admin@12345' \\
        --name "Demo Admin" --role ADMIN

Run it from backend/auth-service with the same .env the service uses.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROLES = ("STUDENT", "RECRUITER", "ADMIN")


def upsert_user(db, *, name: str, email: str, password: str, role: str):
    """Insert the user, or update role/password if the email already exists."""
    from app.core.security import hash_password, validate_password_length
    from app.database.models import User

    from email_validator import EmailNotValidError, validate_email

    try:  # same rule the login form applies, so we never create an account that cannot sign in
        email = validate_email(email, check_deliverability=False).normalized
    except EmailNotValidError as exc:
        raise ValueError(f"invalid email: {exc}") from exc

    role = role.upper()
    if role not in ROLES:
        raise ValueError(f"role must be one of {', '.join(ROLES)}")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    validate_password_length(password)

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(name=name, email=email, password_hash=hash_password(password), role=role)
        db.add(user)
    else:
        if user.role != role:
            user.token_version = (user.token_version or 0) + 1   # sign out old sessions
        user.name = name
        user.role = role
        user.password_hash = hash_password(password)
    user.is_verified = True
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--email", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--role", default="STUDENT", choices=ROLES)
    a = ap.parse_args()

    from app.database import models  # noqa: F401  (registers tables)
    from app.database.database import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = upsert_user(db, name=a.name or a.email.split("@")[0], email=a.email, password=a.password, role=a.role)
        print(f"{user.role} user ready: id={user.id} email={user.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
