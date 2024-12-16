from datetime import datetime
from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, Any, List


class BlockUserRequest(BaseModel):
    is_blocked: bool


class UpdateBio(BaseModel):
    bio: str = Field(..., min_length=1, max_length=500, description="User's bio")

    @validator("bio")
    def validate_bio(cls, value):
        if not value.strip():
            raise ValueError("Bio cannot be empty or only whitespace.")
        return value


class ChangePassword(BaseModel):
    old_password: str = Field(..., min_length=8, description="Current password.")
    new_password: str = Field(..., min_length=8, description="New password.")
    confirm_new_password: str = Field(..., min_length=8, description="Confirm new password.")

    @validator("confirm_new_password")
    def passwords_match(cls, v, values, **kwargs):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("New passwords do not match.")
        return v


class UpdateUser(BaseModel):
    username: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    avatar: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserResponse(BaseModel):
    uuid: str
    username: str
    email: str
    avatar: str
    address: str
    phone_number: str
    bio: str
    gender: str
    date_of_birth: Optional[str]
    roles: List[str]
    is_deleted: bool
    is_active: bool
    is_verified: bool
    is_blocked: bool


class ResendResetPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetPasswordResponse(BaseModel):
    date: str = Field(...)
    status: int = Field(...)
    message: str = Field(...)
    payload: Optional[dict] = Field(None)


class VerifyResetPasswordRequest(BaseModel):
    email: EmailStr = Field(...)
    reset_code: str = Field(...)


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetComplete(BaseModel):
    email: EmailStr
    reset_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @validator("confirm_password")
    def passwords_match(cls, confirm_password: str, values: Any):
        new_password = values.get("new_password")
        if new_password != confirm_password:
            raise ValueError("Passwords do not match.")
        return confirm_password


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class VerifyRequest(BaseModel):
    email: EmailStr
    verification_code: str


class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match 😁")
        return v


class LoginUser(BaseModel):
    email: EmailStr
    password: str

    class Config:
        from_attributes = True
