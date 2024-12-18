from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, HttpUrl, validator
from typing import Optional, List, Union
from enum import Enum as PyEnum
from app.schemas.major import MajorResponse
from app.utils.format_date import format_date


class SchoolType(str, PyEnum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"
    TVET = "TVET"
    MAJORS_COURSES = "MAJORS_COURSES"


class FacultyResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str] = None

    class Config:
        orm_mode = True


class SchoolDetailsResponse(BaseModel):
    uuid: str = Field(...)
    kh_name: str = Field(...)
    en_name: str = Field(...)
    type: SchoolType = Field(...)
    popular_major: str = Field(...)
    logo_url: Optional[str] = Field(None)
    cover_image: Optional[str] = Field(None)
    location: Optional[str] = Field(None)
    phone: Optional[str] = Field(None)
    lowest_price: Optional[float] = Field(None)
    highest_price: Optional[float] = Field(None)
    latitude: Optional[float] = Field(None)
    longitude: Optional[float] = Field(None)
    email: Optional[str] = Field(None)
    website: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    mission: Optional[str] = Field(None)
    vision: Optional[str] = Field(None)
    majors: List[MajorResponse] = Field(...)
    faculties: List[FacultyResponse]

    class Config:
        orm_mode = True


class UploadSchoolLogoCoverRequest(BaseModel):
    logo: Optional[str] = Field(None, description="Base64 or file name for the logo")
    cover_image: Optional[str] = Field(None, description="Base64 or file name for the cover image")


class UploadImageResponse(BaseModel):
    uuid: str = Field(..., description="School UUID")
    logo_url: Optional[str] = Field(None, description="Uploaded logo URL")
    cover_image: Optional[str] = Field(None, description="Uploaded cover image URL")


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
    type: Union[str, SchoolType] = Field(...)
    popular_major: str = Field(..., max_length=255)
    logo_url: Optional[str] = Field(None)
    cover_image: Optional[str] = Field(None)
    location: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=15)
    lowest_price: Optional[float] = Field(None, ge=0)
    highest_price: Optional[float] = Field(None, ge=0)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    email: Optional[EmailStr] = Field(None)
    website: Optional[str] = Field(None)
    description: Optional[str] = Field(None, max_length=2000)
    mission: Optional[str] = Field(None, max_length=2000)
    vision: Optional[str] = Field(None, max_length=2000)


class UpdateSchoolRequest(BaseModel):

    kh_name: Optional[str] = Field(None)
    en_name: Optional[str] = Field(None)
    popular_major: Optional[str] = Field(None)
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
    province_name: Optional[str] = None
    kh_name: str
    en_name: str
    popular_major: str
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
    def format_datetime(cls, value: Optional[datetime]) -> Optional[str]:
        return format_date(value) if value else None

    class Config:
        from_attributes = True
