import uuid

from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import List, Optional
from datetime import datetime


class JobQueryParams(BaseModel):
    job_category_uuid: Optional[uuid.UUID] = None
    province_uuid: Optional[uuid.UUID] = None
    job_type: Optional[str] = None
    page: int = 1
    page_size: int = 10

    class Config:
        from_attributes = True


class JobListingResponse(BaseModel):
    uuid: uuid.UUID
    job_type: str
    position: Optional[str] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    province_name: Optional[str] = None

    class Config:
        from_attributes = True


# class JobUpdateRequest(BaseModel):
#     type: Optional[str] = Field(None, description="Job type (Full-time, Part-time, etc.)")
#     position: Optional[str] = Field(None, max_length=255)
#     qualification: Optional[str] = Field(None, max_length=255)
#     published_date: Optional[str] = Field(None, description="Published date (e.g., 2024-12-05T12:00:00)")
#     description: Optional[str] = Field(None)
#     responsibilities: Optional[str] = Field(None)
#     requirements: Optional[str] = Field(None)
#     resources: Optional[str] = Field(None)
#     salaries: Optional[float] = Field(None, description="Salary offered by the client")
#     job_category_uuid: Optional[uuid.UUID] = Field(None, description="Job Category UUID")
#     province_uuid: Optional[uuid.UUID] = Field(None, description="Province UUID")
#     company_uuid: Optional[uuid.UUID] = Field(None, description="Company UUID")
#
#     class Config:
#         from_attributes = True


class JobUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, description="Job title")
    company: Optional[str] = Field(None, description="Company name")
    logo: Optional[str] = Field(None, description="Logo URL as a string")
    facebook_url: Optional[str] = Field(None, description="Facebook URL as a string")
    location: Optional[str] = Field(None, description="Job location")
    posted_at: Optional[datetime] = Field(None, description="Posting date")
    description: Optional[str] = Field(None, description="Job description")
    category: Optional[str] = Field(None, description="Job category")
    job_type: Optional[str] = Field(None, description="Job type")
    schedule: Optional[str] = Field(None, description="Work schedule")
    salary: Optional[str] = Field(None, description="Salary range")
    closing_date: Optional[datetime] = Field(None, description="Closing date for application")
    requirements: Optional[List[str]] = Field(None, description="Job requirements")
    responsibilities: Optional[List[str]] = Field(None, description="Job responsibilities")
    benefits: Optional[List[str]] = Field(None, description="Job benefits")
    email: Optional[str] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone")
    website: Optional[str] = Field(None, description="Company website URL")
    is_active: Optional[bool] = Field(None, description="Job active status")

    class Config:
        from_attributes = True


# class JobCreateRequest(BaseModel):
#     type: # str = Field(..., description="Job type (Full-time, Part-time, etc.)")
#     position: Optional[str] = Field(None, max_length=255)
#     qualification: Optional[str] = Field(None, max_length=255)
#     published_date: Optional[str] = Field(None, description="Published date (e.g., 2024-12-05T12:00:00)")
#     description: Optional[str] = Field(None)
#     responsibilities: Optional[str] = Field(None)
#     requirements: Optional[str] = Field(None)
#     resources: Optional[str] = Field(None)
#     job_category_uuid: uuid.UUID = Field(...)
#     province_uuid: Optional[uuid.UUID] = Field(None)
#     company_uuid: Optional[uuid.UUID] = Field(None)
#     salaries: Optional[float] = Field(None, description="Salary offered by the client")
#
#     class Config:
#         from_attributes = True


class JobCreateRequest(BaseModel):
    title: str
    company: str
    logo: Optional[str] = Field(None, description="Logo URL as a string")
    facebook_url: Optional[str] = Field(None, description="Facebook URL as a string")
    location: Optional[str]
    posted_at: Optional[datetime]
    description: Optional[str]
    category: Optional[str]
    job_type: Optional[str]
    schedule: Optional[str]
    salary: Optional[str]
    closing_date: Optional[datetime]
    requirements: Optional[List[str]]
    responsibilities: Optional[List[str]]
    benefits: Optional[List[str]]
    email: Optional[str]
    phone: Optional[str]
    website: Optional[str] = Field(None, description="Website URL as a string")
    is_active: bool = True

# class JobResponse(BaseModel):
#     uuid: uuid.UUID
#     type: str
#     position: Optional[str] = None
#     qualification: Optional[str] = None
#     published_date: Optional[str] = None
#     description: Optional[str] = None
#     responsibilities: Optional[str] = None
#     requirements: Optional[str] = None
#     resources: Optional[str] = None
#     salaries: Optional[float] = None
#     job_category_uuid: uuid.UUID
#     company_uuid: Optional[uuid.UUID] = None
#     province_uuid: Optional[uuid.UUID] = None
#
#     class Config:
#         from_attributes = True


class JobResponse(BaseModel):
    uuid: str
    title: str
    company: str
    logo: Optional[str]
    facebook_url: Optional[str]
    location: Optional[str]
    posted_at: Optional[datetime]
    description: Optional[str]
    category: Optional[str]
    job_type: Optional[str]
    schedule: Optional[str]
    salary: Optional[str]
    closing_date: Optional[datetime]
    requirements: Optional[List[str]]
    responsibilities: Optional[List[str]]
    benefits: Optional[List[str]]
    email: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


