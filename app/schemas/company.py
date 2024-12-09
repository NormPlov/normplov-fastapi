import uuid
from typing import Optional
from pydantic import BaseModel, Field


class CompanyResponse(BaseModel):
    company_uuid: uuid.UUID
    company_name: str
    company_address: Optional[str] = None
    company_logo: Optional[str] = None
    company_website: Optional[str] = None
    company_linkedin: Optional[str] = None
    company_twitter: Optional[str] = None
    company_facebook: Optional[str] = None
    company_instagram: Optional[str] = None

    class Config:
        from_attributes = True


class CompanyCreateRequest(BaseModel):
    name: str = Field(...)
    address: Optional[str] = Field(None)
    linkedin: Optional[str] = Field(None)
    twitter: Optional[str] = Field(None)
    facebook: Optional[str] = Field(None)
    instagram: Optional[str] = Field(None)
    website: Optional[str] = Field(None)

    class Config:
        from_attributes = True