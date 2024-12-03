from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, HttpUrl, validator
from typing import Optional
from enum import Enum as PyEnum

from app.utils.format_date import format_date


class SchoolType(PyEnum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"
    TVET = "TVET"
    MAJORS_COURSES = "MAJORS_COURSES"


class CreateSchoolRequest(BaseModel):
    kh_name: str = Field(..., max_length=255, description="Khmer name of the school")
    en_name: str = Field(..., max_length=255, description="English name of the school")
    type: SchoolType = Field(..., description="Type of the school")
    logo_url: Optional[HttpUrl] = Field(None, description="Logo URL of the school")
    cover_image: Optional[HttpUrl] = Field(None, description="Cover image URL of the school")
    location: Optional[str] = Field(None, max_length=500, description="Location of the school")
    phone: Optional[str] = Field(None, max_length=15, description="Phone number of the school")
    lowest_price: Optional[float] = Field(None, ge=0, description="Lowest tuition fee offered by the school")
    highest_price: Optional[float] = Field(None, ge=0, description="Highest tuition fee offered by the school")
    map: Optional[HttpUrl] = Field(None, description="Google Maps link of the school location")
    email: Optional[EmailStr] = Field(None, description="Contact email of the school")
    website: Optional[HttpUrl] = Field(None, description="Website of the school")
    description: Optional[str] = Field(None, max_length=2000, description="Description of the school")
    mission: Optional[str] = Field(None, max_length=2000, description="Mission statement of the school")
    vision: Optional[str] = Field(None, max_length=2000, description="Vision statement of the school")


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
    id: int
    uuid: str
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

    class Config:
        from_attributes = True

    @validator("uuid", pre=True)
    def convert_uuid_to_str(cls, value: UUID) -> str:
        if isinstance(value, UUID):
            return str(value)
        return value

    @validator("created_at", "updated_at", pre=True)
    def format_datetime(cls, value: datetime) -> str:
        return format_date(value) if value else None
