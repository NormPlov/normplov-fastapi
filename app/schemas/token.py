from datetime import datetime
from pydantic import BaseModel


class OAuthCallbackRequest(BaseModel):
    code: str


class BaseResponse(BaseModel):
    status: int
    message: str
    date: datetime
    payload: dict


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    message: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
