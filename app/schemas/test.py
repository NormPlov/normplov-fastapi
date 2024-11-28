from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List, Dict


class TestSummary(BaseModel):
    test_uuid: str
    test_name: str
    is_completed: bool
    is_deleted: bool
    created_at: str

    @validator("created_at", pre=True)
    def format_datetime(cls, value):
        if isinstance(value, datetime):
            return value.strftime("%A, %d %B")
        return value


class UserTestsResponse(BaseModel):
    user_id: int
    tests: List[TestSummary]


class GetTestDetailsInput(BaseModel):
    test_uuid: str = Field(..., description="Unique identifier for the test")


class AssessmentDraftData(BaseModel):
    responses: Dict[str, int]


class AssessmentData(BaseModel):
    assessment_type_uuid: str
    assessment_type_name: str
    is_draft: bool
    draft_data: Optional[AssessmentDraftData]
    completion_status: str


class GetTestDetailsResponse(BaseModel):
    test_uuid: str
    test_name: str
    assessments: List[AssessmentData]
