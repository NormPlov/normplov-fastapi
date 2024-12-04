from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum


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
    career_uuids: List[str] = Field(..., description="List of career UUIDs associated with the major.")
    school_uuids: List[str] = Field(..., description="List of school UUIDs offering the major.")


class MajorResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str]
    fee_per_year: Optional[float]
    duration_years: Optional[int]
    degree: DegreeTypeEnum
    created_at: datetime
    updated_at: datetime

    @validator("uuid", pre=True)
    def uuid_to_string(cls, value):
        if isinstance(value, UUID):
            return str(value)
        return value

    class Config:
        from_attributes = True
