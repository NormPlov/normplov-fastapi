from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, validator, UUID4
from typing import Optional, List
from enum import Enum


class CareerResponse(BaseModel):
    uuid: str = Field(...)
    name: str = Field(...)
    created_at: str = Field(...)
    updated_at: Optional[str] = Field(None)


class MajorCareersResponse(BaseModel):
    major_uuid: str = Field(...)
    careers: List[CareerResponse] = Field(...)


class DegreeTypeEnum(str, Enum):
    ASSOCIATE = "ASSOCIATE"
    BACHELOR = "BACHELOR"
    MASTER = "MASTER"
    PHD = "PHD"


class CreateMajorRequest(BaseModel):
    name: str = Field(..., description="The name of the major.")
    description: Optional[str] = Field(None, description="Description of the major.")
    fee_per_year: Optional[float] = Field(None, description="Annual fee for the major.")
    duration_years: Optional[int] = Field(None, description="Duration of the program in years.")
    degree: DegreeTypeEnum = Field(..., description="The degree type for the major.")
    faculty_uuid: UUID4 = Field(..., description="The UUID of the faculty associated with the major.")
    career_uuids: List[str] = Field(..., description="List of career UUIDs associated with the major.")


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
