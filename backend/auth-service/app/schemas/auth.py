from pydantic import BaseModel, EmailStr
from typing import Literal


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Literal[
        "STUDENT",
        "RECRUITER",
        "ADMIN"
    ] = "STUDENT"


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True