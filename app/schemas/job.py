import uuid

from pydantic import BaseModel, Field
from typing import Optional


class JobUpdateRequest(BaseModel):
    type: Optional[str] = Field(None, description="Job type (Full-time, Part-time, etc.)")
    position: Optional[str] = Field(None, max_length=255)
    qualification: Optional[str] = Field(None, max_length=255)
    published_date: Optional[str] = Field(None, description="Published date (e.g., 2024-12-05T12:00:00)")
    description: Optional[str] = Field(None)
    responsibilities: Optional[str] = Field(None)
    requirements: Optional[str] = Field(None)
    resources: Optional[str] = Field(None)
    salaries: Optional[float] = Field(None, description="Salary offered by the client")
    job_category_uuid: Optional[uuid.UUID] = Field(None, description="Job Category UUID")
    province_uuid: Optional[uuid.UUID] = Field(None, description="Province UUID")
    company_uuid: Optional[uuid.UUID] = Field(None, description="Company UUID")

    class Config:
        from_attributes = True


class JobCreateRequest(BaseModel):
    type: str = Field(..., description="Job type (Full-time, Part-time, etc.)")
    position: Optional[str] = Field(None, max_length=255)
    qualification: Optional[str] = Field(None, max_length=255)
    published_date: Optional[str] = Field(None, description="Published date (e.g., 2024-12-05T12:00:00)")
    description: Optional[str] = Field(None)
    responsibilities: Optional[str] = Field(None)
    requirements: Optional[str] = Field(None)
    resources: Optional[str] = Field(None)
    job_category_uuid: uuid.UUID = Field(...)
    province_uuid: Optional[uuid.UUID] = Field(None)
    company_uuid: Optional[uuid.UUID] = Field(None)
    salaries: Optional[float] = Field(None, description="Salary offered by the client")

    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    uuid: uuid.UUID
    type: str
    position: Optional[str] = None
    qualification: Optional[str] = None
    published_date: Optional[str] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    resources: Optional[str] = None
    salaries: Optional[float] = None
    job_category_uuid: uuid.UUID
    company_uuid: Optional[uuid.UUID] = None
    province_uuid: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True
