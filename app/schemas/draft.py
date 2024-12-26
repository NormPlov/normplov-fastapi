from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import Dict, Optional, Union


class SubmitDraftAssessmentRequest(BaseModel):
    responses: Dict[str, Union[int, float]] = Field(
        ..., description="The updated responses for the assessment."
    )

    @validator("responses")
    def validate_scores(cls, responses):
        if not responses:
            raise ValueError("Responses cannot be empty.")
        for key, value in responses.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Invalid score for {key}: {value}. Must be a number (int or float).")
            if value < 0:
                raise ValueError(f"Score for {key} must be non-negative.")
        return responses


class DraftItem(BaseModel):
    uuid: str = Field(...)
    draft_name: str = Field(...)
    assessment_name: str = Field(...)
    created_at: str = Field(...)
    updated_at: Optional[str] = Field(None)
    response_data: Dict = Field(...)


class SaveDraftRequest(BaseModel):
    responses: Dict = Field(..., description="The draft response data as a dictionary.")


class DraftResponse(BaseModel):
    draft_uuid: str
    draft_name: str
    response_data: Dict
    created_at: datetime
    updated_at: Optional[datetime]



