from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, HttpUrl, validator
from typing import Optional, List
from enum import Enum as PyEnum

from app.schemas.major import MajorResponse
from app.utils.format_date import format_date


class SchoolType(PyEnum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"
    TVET = "TVET"
    MAJORS_COURSES = "MAJORS_COURSES"


class SchoolMajorsResponse(BaseModel):
    school_uuid: str = Field(...)
    majors: List[MajorResponse] = Field(...)
    metadata: dict = Field(...)


class CreateSchoolRequest(BaseModel):
    province_uuid: str = Field(...)
    kh_name: str = Field(..., max_length=255)
    en_name: str = Field(..., max_length=255)
    type: SchoolType = Field(...)
    logo_url: Optional[HttpUrl] = Field(None)
    cover_image: Optional[HttpUrl] = Field(None)
    location: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=15)
    lowest_price: Optional[float] = Field(None, ge=0)
    highest_price: Optional[float] = Field(None, ge=0)
    map: Optional[HttpUrl] = Field(None)
    email: Optional[EmailStr] = Field(None)
    website: Optional[HttpUrl] = Field(None)
    description: Optional[str] = Field(None, max_length=2000)
    mission: Optional[str] = Field(None, max_length=2000)
    vision: Optional[str] = Field(None, max_length=2000)


class UpdateSchoolRequest(BaseModel):

    kh_name: Optional[str] = Field(None)
    en_name: Optional[str] = Field(None)
    type: Optional[SchoolType] = Field(None)
    logo_url: Optional[HttpUrl] = Field(None)
    cover_image: Optional[HttpUrl] = Field(None)
    location: Optional[str] = Field(None)
    phone: Optional[str] = Field(None)
    lowest_price: Optional[float] = Field(None)
    highest_price: Optional[float] = Field(None)
    map: Optional[HttpUrl] = Field(None)
    email: Optional[EmailStr] = Field(None)
    website: Optional[HttpUrl] = Field(None)
    description: Optional[str] = Field(None)
    mission: Optional[str] = Field(None)
    vision: Optional[str] = Field(None)


class SchoolResponse(BaseModel):
    uuid: str
    province_name: Optional[str]
    kh_name: str
    en_name: str
    type: str
    logo_url: Optional[str]
    cover_image: Optional[str]
    location: Optional[str]
    phone: Optional[str]
    lowest_price: Optional[float]
    highest_price: Optional[float]
    map: Optional[str]
    email: Optional[str]
    website: Optional[str]
    description: Optional[str]
    mission: Optional[str]
    vision: Optional[str]
    is_deleted: bool
    created_at: str
    updated_at: str

    @validator("uuid", pre=True)
    def convert_uuid_to_str(cls, value: UUID) -> str:
        if isinstance(value, UUID):
            return str(value)
        return value

    @validator("created_at", "updated_at", pre=True)
    def format_datetime(cls, value: datetime) -> str:
        return format_date(value) if value else None

    class Config:
        from_attributes = True
