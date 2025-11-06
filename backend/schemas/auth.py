"""Authentication schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserSignup(BaseModel):
    """User signup request schema."""

    email: EmailStr
    password: str
    name: str

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password length."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize name by stripping whitespace."""
        return v.strip() if isinstance(v, str) else v


class UserResponse(BaseModel):
    """User response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    role: str
    created_at: str


class UserLogin(BaseModel):
    """User login request schema."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Login response schema with token and user info."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
