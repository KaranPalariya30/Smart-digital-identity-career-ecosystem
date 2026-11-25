
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from typing import Literal


def validate_password_bytes(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes.")
    return password


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: Literal["STUDENT"] = "STUDENT"

    _validate_password = field_validator("password")(
        validate_password_bytes
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

    model_config = ConfigDict(from_attributes=True)


class EmailVerificationRequest(BaseModel):
    token: str


class RegistrationResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    is_verified: bool
    verification_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

    _validate_password = field_validator("new_password")(
        validate_password_bytes
    )
