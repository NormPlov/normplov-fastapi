from pydantic import BaseModel, Field
from typing import Optional, List
from app.schemas.payload import BaseResponse


class CreateJobCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the job category")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the job category")

    class Config:
        orm_mode = True


class JobCategoryDetails(BaseModel):
    uuid: str
    name: str
    description: Optional[str]
    is_deleted: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        orm_mode = True


class AllJobCategoriesResponse(BaseResponse):
    payload: List[JobCategoryDetails]


class CreateJobCategoryResponse(BaseModel):
    date: str = Field(..., description="The date of the response in YYYY-MM-DD format.")
    status: int = Field(..., description="HTTP status code.")
    message: str = Field(..., description="Response message.")
    payload: Optional[dict] = Field(None, description="Additional data for the response.")

    class Config:
        orm_mode = True


class UpdateJobCategoryRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=255, description="Updated name of the job category")
    description: Optional[str] = Field(None, max_length=1000, description="Updated description of the job category")

    class Config:
        orm_mode = True


class UpdateJobCategoryResponse(BaseModel):
    date: str
    status: int
    message: str
    payload: Optional[dict] = None


class DeleteJobCategoryResponse(BaseModel):
    date: str
    status: int
    message: str
