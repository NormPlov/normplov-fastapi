from uuid import UUID
from pydantic import BaseModel, Field, validator, UUID4
from typing import Optional, List
from enum import Enum


class UpdateMajorRequest(BaseModel):
    name: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    fee_per_year: Optional[float] = Field(None)
    duration_years: Optional[int] = Field(None)
    degree: Optional[str] = Field(None)
    faculty_uuid: Optional[UUID4] = Field(None)


class CareerResponse(BaseModel):
    uuid: str = Field(...)
    name: str = Field(...)
    created_at: str = Field(...)
    updated_at: Optional[str] = Field(None)


class MajorCareersResponse(BaseModel):
    major_uuid: str = Field(...)


class DegreeTypeEnum(str, Enum):
    ASSOCIATE = "ASSOCIATE"
    BACHELOR = "BACHELOR"
    MASTER = "MASTER"
    PHD = "PHD"


class CreateMajorRequest(BaseModel):
    name: str = Field(...)
    description: Optional[str] = Field(None)
    fee_per_year: Optional[float] = Field(None)
    duration_years: Optional[int] = Field(None)
    degree: DegreeTypeEnum = Field(...)
    faculty_uuid: UUID4 = Field(...)


class MajorResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str]
    fee_per_year: Optional[float]
    duration_years: Optional[int]
    degree: DegreeTypeEnum


    @validator("uuid", pre=True)
    def uuid_to_string(cls, value):
        if isinstance(value, UUID):
            return str(value)
        return value

    class Config:
        from_attributes = True
