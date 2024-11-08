from datetime import datetime
from pydantic import BaseModel, EmailStr, validator

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetComplete(BaseModel):
    token: str
    new_password: str

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

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    is_verified: bool
    registered_at: datetime

class LoginUserDto(BaseModel):
    username: str
    password: str

    class Config:
        from_attributes = True
