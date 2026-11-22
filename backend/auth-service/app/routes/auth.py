from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from app.core.config import (
    EMAIL_VERIFICATION_DEV_MODE,
    FRONTEND_VERIFY_BASE_URL,
    FRONTEND_RESET_PASSWORD_BASE_URL
)
from app.core.email import send_auth_email

from app.core.config import EMAIL_VERIFICATION_DEV_MODE
from app.database.database import get_db
from app.database.models import User
from app.schemas.auth import (
    UserRegister,
    UserResponse,
    UserLogin,
    TokenResponse,
    RegistrationResponse,
    EmailVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    create_email_verification_token,
    decode_email_verification_token,
    create_password_reset_token,
    decode_password_reset_token,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

bearer_scheme = HTTPBearer()


# 1. USER REGISTRATION
@router.post(
    "/register",
    response_model=RegistrationResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED
)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    verification_token = create_email_verification_token(new_user.id)

    response_data = {
        "id": new_user.id,
        "name": new_user.name,
        "email": new_user.email,
        "role": new_user.role,
        "is_verified": new_user.is_verified,
    }

    if EMAIL_VERIFICATION_DEV_MODE:
        response_data["verification_token"] = verification_token
    else:
        verification_link = (
            f"{FRONTEND_VERIFY_BASE_URL}?token={verification_token}"
        )

        try:
            send_auth_email(
                to_email=new_user.email,
                subject="Verify Your Email - Smart Digital Identity",
                body=(
                    f"Hello {new_user.name},\n\n"
                    "Thank you for registering.\n"
                    "Please verify your email using the link below:\n\n"
                    f"{verification_link}\n\n"
                    "If you did not create this account, ignore this email."
                )
            )
        except Exception:
            db.delete(new_user)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to send verification email. Please try again later."
            )
    return response_data


# 2. USER LOGIN
@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if not user or not verify_password(
        user_data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "token_version": user.token_version
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# 3. CURRENT USER AUTHENTICATION
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user_id = int(user_id)

    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()

    if (
        user is None
        or not user.is_active
        or payload.get("token_version") != user.token_version
    ):
        raise credentials_exception

    return user


# 4. PROTECTED PROFILE API
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# 5. ROLE-BASED ACCESS CONTROL
def require_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        return current_user

    return role_checker


@router.get("/student-only")
def student_only(
    current_user: User = Depends(require_role("STUDENT"))
):
    return {
        "message": "Student access granted",
        "user": current_user.name
    }


@router.get("/recruiter-only")
def recruiter_only(
    current_user: User = Depends(require_role("RECRUITER"))
):
    return {
        "message": "Recruiter access granted",
        "user": current_user.name
    }


@router.get("/admin-only")
def admin_only(
    current_user: User = Depends(require_role("ADMIN"))
):
    return {
        "message": "Admin access granted",
        "user": current_user.name
    }


# 6. EMAIL VERIFICATION
@router.post("/verify-email")
def verify_email(
    verification_data: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    try:
        payload = decode_email_verification_token(
            verification_data.token
        )
        user_id = int(payload.get("sub"))

    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.is_verified:
        return {"message": "Email is already verified"}

    user.is_verified = True
    db.commit()

    return {"message": "Email verified successfully"}

# 7. FORGOT PASSWORD

@router.post("/forgot-password")
def forgot_password(
    request_data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == request_data.email
    ).first()

    response_data = {
        "message": "If the account exists, password reset instructions have been generated."
    }

    if not user:
        return response_data

    reset_token = create_password_reset_token(
        user.id,
        user.token_version
    )

    if EMAIL_VERIFICATION_DEV_MODE:
        response_data["reset_token"] = reset_token
    else:
        reset_link = (
            f"{FRONTEND_RESET_PASSWORD_BASE_URL}?token={reset_token}"
        )

        try:
            send_auth_email(
                to_email=user.email,
                subject="Password Reset - Smart Digital Identity",
                body=(
                    f"Hello {user.name},\n\n"
                    "We received a request to reset your password.\n"
                    "Use the link below to reset it:\n\n"
                    f"{reset_link}\n\n"
                    "If you did not request this, please ignore this email."
                )
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to process the request right now. Please try again later."
            )

    return response_data


# 8. RESET PASSWORD
@router.post("/reset-password")
def reset_password(
    request_data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    # Validate password length
    if len(request_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    # Validate reset token
    try:
        payload = decode_password_reset_token(request_data.token)
        user_id = int(payload.get("sub"))

    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token"
        )

    # Find user
    # Find user
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token"
        )

    if payload.get("token_version") != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token"
        )

    # Hash and update new password
    user.password_hash = hash_password(request_data.new_password)
    user.token_version += 1

    db.commit()

    return {"message": "Password reset successfully"}