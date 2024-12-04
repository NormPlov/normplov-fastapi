from pydantic import BaseModel, Field
from typing import Optional, List


class FacultyUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Name of the faculty")
    description: Optional[str] = Field(None, description="Description of the faculty")


class FacultyDetail(BaseModel):
    uuid: str
    name: str
    description: str
    school_name: str
    created_at: str
    updated_at: str


class CreateFacultyRequest(BaseModel):
    name: str = Field(..., max_length=255, description="Name of the faculty")
    description: Optional[str] = Field(None, description="Description of the faculty")
    school_uuid: str = Field(..., description="UUID of the school to which the faculty belongs")


class FacultyListResponse(BaseModel):
    faculties: List[FacultyDetail]
    metadata: dict

    class Config:
        orm_mode = True
