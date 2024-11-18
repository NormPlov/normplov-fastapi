from datetime import datetime
from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional


class ChangePasswordDto(BaseModel):
    old_password: str = Field(..., min_length=8, description="Current password.")
    new_password: str = Field(..., min_length=8, description="New password.")
    confirm_new_password: str = Field(..., min_length=8, description="Confirm new password.")

    @validator("confirm_new_password")
    def passwords_match(cls, v, values, **kwargs):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("New passwords do not match.")
        return v



class UpdateUserDto(BaseModel):
    username: Optional[str]
    address: Optional[str]
    phone_number: Optional[str]
    bio: Optional[str]
    gender: Optional[str]
    date_of_birth: Optional[datetime]

class UserResponseDto(BaseModel):
    uuid: str
    username: str
    email: str
    avatar: str
    address: str
    phone_number: str
    bio: str
    gender: str
    date_of_birth: Optional[datetime]
    is_deleted: bool
    is_active: bool
    is_verified: bool
    registered_at: Optional[datetime]


class PasswordResetRequestDto(BaseModel):
    email: str

class PasswordResetCompleteDto(BaseModel):
    email: EmailStr
    token: str = Field(..., min_length=6, max_length=6, description="Password reset token.")
    new_password: str = Field(..., min_length=8, description="New password.")

class UserCreateRequestDto(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match 😁")
        return v


class LoginUserDto(BaseModel):
    email: EmailStr
    password: str

    class Config:
        from_attributes = True
