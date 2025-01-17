from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class UserTestResponse(BaseModel):
    test_uuid: str
    test_name: str
    assessment_type_name: str

    class Config:
        from_attributes = True


class UserTestWithUserSchema(BaseModel):
    test_uuid: str
    test_name: str
    assessment_type_name: Optional[str]
    user_avatar: Optional[str]
    user_name: str
    user_email: str
    response_data: List[Dict[str, Any]]
    is_draft: bool
    is_completed: bool
    created_at: datetime


class PaginationMetadata(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class PaginatedUserTestsWithUsersResponse(BaseModel):
    tests: List[UserTestWithUserSchema]
    metadata: PaginationMetadata


class UserTestResponseSchema(BaseModel):
    test_uuid: str
    test_name: str
    assessment_type_name: Optional[str]
    response_data: List[Dict[str, Any]]
    created_at: datetime


class PaginationMetadata(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class PaginatedUserTestsResponse(BaseModel):
    tests: list[UserTestResponseSchema]
    metadata: PaginationMetadata


class AssessmentDraftData(BaseModel):
    responses: Dict[str, int]


class AssessmentData(BaseModel):
    assessment_type_uuid: str
    assessment_type_name: str
    is_draft: bool
    draft_data: Optional[AssessmentDraftData]
    completion_status: str

