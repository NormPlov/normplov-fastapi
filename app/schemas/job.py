import uuid

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class JobDetailsWithBookmarkResponse(BaseModel):
    uuid: uuid.UUID
    title: str
    company_name: str
    logo: Optional[str]
    location: Optional[str]
    job_type: Optional[str]
    posted_at: datetime
    posted_at_days_ago: Optional[str]
    schedule: Optional[str]
    salary: Optional[str]
    is_scraped: bool
    description: Optional[str]
    requirements: Optional[List[str]]
    responsibilities: Optional[List[str]]
    benefits: Optional[List[str]]
    facebook_url: Optional[str]
    email: Optional[str]
    phone: Optional[List[str]]
    website: Optional[str]
    created_at: datetime
    created_at_days_ago: Optional[str]
    closing_date: Optional[str]
    category: Optional[str]
    visitor_count: int

    class Config:
        from_attributes = True


class JobDetailsResponse(BaseModel):
    uuid: uuid.UUID
    title: str
    company_name: str
    logo: Optional[str]
    location: Optional[str]
    job_type: Optional[str]
    posted_at: datetime
    schedule: Optional[str]
    salary: Optional[str]
    is_scraped: bool
    description: Optional[str]
    requirements: Optional[List[str]]
    responsibilities: Optional[List[str]]
    benefits: Optional[List[str]]
    facebook_url: Optional[str]
    email: Optional[str]
    phone: Optional[List[str]]
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


class CustomJobListingResponse(BaseModel):
    bookmark_uuid: uuid.UUID
    job_uuid: uuid.UUID
    job_type: str
    title: Optional[str] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    province_name: Optional[str] = None
    closing_date: Optional[datetime] = None

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
    title: Optional[str] = None
    category: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    facebook_url: Optional[str] = None
    posted_at: Optional[str] = None
    description: Optional[str] = None
    job_type: Optional[str] = None
    schedule: Optional[str] = None
    salary: Optional[str] = None
    closing_date: Optional[str] = None
    requirements: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    email: Optional[str] = None
    phone: Optional[List[str]] = None
    website: Optional[str] = None
    logo: Optional[str] = None

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class JobCreateRequest(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    facebook_url: Optional[str] = None
    posted_at: Optional[str] = None
    description: Optional[str] = None
    job_type: Optional[str] = None
    schedule: Optional[str] = None
    salary: Optional[str] = None
    closing_date: Optional[str] = None
    requirements: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    email: Optional[str] = None
    phone: Optional[List[str]] = None
    website: Optional[str] = None
    is_active: bool = True
    logo: Optional[str] = None
    category: Optional[str] = None


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
    phone: Optional[List[str]]
    website: Optional[str]

    class Config:
        from_attributes = True


