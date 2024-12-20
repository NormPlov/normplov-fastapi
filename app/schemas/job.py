import uuid

from fastapi import HTTPException
from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import List, Optional
from datetime import datetime


class JobDetailsResponse(BaseModel):
    uuid: uuid.UUID
    title: str
    company_name: str
    logo: Optional[str]
    location: Optional[str]
    job_type: Optional[str]
    description: Optional[str]
    requirements: Optional[List[str]]
    responsibilities: Optional[List[str]]
    facebook_url: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    created_at: datetime
    closing_date: Optional[str]
    category: Optional[str]

    class Config:
        from_attributes = True


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
    title: Optional[str] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    province_name: Optional[str] = None
    closing_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, description="Job title")
    company: Optional[str] = Field(None, description="Company name")
    logo: Optional[str] = Field(None, description="Logo URL as a string")
    facebook_url: Optional[str] = Field(None, description="Facebook URL as a string")
    location: Optional[str] = Field(None, description="Job location")
    posted_at: Optional[datetime] = Field(None, description="Posting date")
    description: Optional[str] = Field(None, description="Job description")
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


class JobCreateRequest(BaseModel):
    job_category_uuid: Optional[str] = Field(None, description="UUID of the job category")
    title: str
    company: str
    logo: Optional[str] = Field(None, description="Logo URL as a string")
    facebook_url: Optional[str] = Field(None, description="Facebook URL as a string")
    location: Optional[str]
    posted_at: Optional[datetime]
    description: Optional[str]
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


class JobResponse(BaseModel):
    uuid: str
    title: str
    category: str
    company: str
    logo: Optional[str]
    facebook_url: Optional[str]
    location: Optional[str]
    posted_at: Optional[datetime]
    description: Optional[str]
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

    class Config:
        from_attributes = True


