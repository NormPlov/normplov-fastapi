from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union, Dict, Any
from enum import Enum as PyEnum
from app.schemas.major import MajorResponse
from app.utils.format_date import format_date


class SchoolType(str, PyEnum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"
    TVET = "TVET"
    MAJORS_COURSES = "MAJORS_COURSES"


class PaginatedMajorsResponse(BaseModel):
    items: List[MajorResponse]
    metadata: Dict[str, Any]


class FacultyResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str]
    majors: PaginatedMajorsResponse

    class Config:
        orm_mode = True


class SchoolDetailsResponse(BaseModel):
    uuid: str
    kh_name: Optional[str]
    en_name: str
    type: SchoolType
    popular_major: str
    logo_url: Optional[str]
    cover_image: Optional[str]
    location: Optional[str]
    phone: Optional[str]
    lowest_price: Optional[float]
    highest_price: Optional[float]
    map_url: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    email: Optional[str]
    website: Optional[str]
    description: Optional[str]
    mission: Optional[str]
    vision: Optional[str]
    is_popular: Optional[bool]
    faculties: List[FacultyResponse]

    class Config:
        orm_mode = True


class SchoolMajorsResponse(BaseModel):
    school_uuid: str = Field(...)
    majors: List[MajorResponse] = Field(...)
    metadata: dict = Field(...)


class CreateSchoolRequest(BaseModel):
    kh_name: str
    en_name: str
    school_type: str
    popular_major: str
    location: Optional[str]
    phone: Optional[str]
    lowest_price: Optional[float]
    highest_price: Optional[float]
    map_url: Optional[str]
    email: Optional[str]
    website: Optional[str]
    description: Optional[str]
    mission: Optional[str]
    vision: Optional[str]
    logo: Optional[str]
    cover_image: Optional[str]
    is_popular: Optional[bool] = False
    is_recommended: Optional[bool] = False


class UpdateSchoolRequest(BaseModel):
    kh_name: Optional[str] = Field(None)
    en_name: Optional[str] = Field(None)
    popular_major: Optional[str] = Field(None)
    type: Optional[Union[str, SchoolType]] = Field(None)
    logo_url: Optional[str] = Field(None)
    cover_image: Optional[str] = Field(None)
    location: Optional[str] = Field(None)
    phone: Optional[str] = Field(None)
    lowest_price: Optional[float] = Field(None)
    highest_price: Optional[float] = Field(None)
    map_url: Optional[str] = Field(None)
    email: Optional[str] = Field(None)
    website: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    mission: Optional[str] = Field(None)
    vision: Optional[str] = Field(None)
    is_popular: Optional[bool] = Field(None)

    @validator("type", pre=True)
    def validate_type(cls, v):
        if isinstance(v, str):
            try:
                return SchoolType(v).value
            except ValueError:
                raise ValueError(f"Invalid school type: {v}. Allowed values: {[e.value for e in SchoolType]}")
        elif isinstance(v, SchoolType):
            return v.value
        return v


class SchoolResponse(BaseModel):
    uuid: str
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
    is_recommended: bool
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
