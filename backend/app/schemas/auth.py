import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_email(value: str) -> str:
    value = value.strip().lower()

    # Accept normal emails and local development domains such as .local
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    if not re.match(pattern, value):
        raise ValueError("Invalid email address")

    return value


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str
    phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return validate_email(value)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        checks = [r"[A-Z]", r"[a-z]", r"\d", r"[^A-Za-z0-9]"]
        if not all(re.search(pattern, value) for pattern in checks):
            raise ValueError(
                "Password needs uppercase, lowercase, a number and a special character"
            )
        return value


class LoginIn(BaseModel):
    email: str
    password: str = Field(max_length=72)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return validate_email(value)


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    phone: str | None
    role: str
    is_active: bool
    created_at: datetime
    last_login: datetime | None


class AuthOut(TokenOut):
    user: UserOut