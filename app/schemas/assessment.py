from pydantic import BaseModel, root_validator
from datetime import datetime
from typing import Any, List


class AssessmentResponseData(BaseModel):
    assessment_type: str
    response_data: Any
    created_at: str

    @root_validator(pre=True)
    def format_created_at(cls, values):
        created_at = values.get("created_at")
        if isinstance(created_at, datetime):
            values["created_at"] = created_at.strftime("%A, %d, %Y")
        return values


class AssessmentResponseList(BaseModel):
    test_uuid: str
    responses: List[AssessmentResponseData]
