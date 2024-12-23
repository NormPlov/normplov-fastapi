from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator

from app.schemas.payload import BaseResponse


class InterestAssessmentInput(BaseModel):
    responses: Dict[str, int] = Field(
        ..., description="Mapping of question keys to user responses (1-5 scale)."
    )

    @validator("responses")
    def validate_responses(cls, responses):
        for key, value in responses.items():
            if not (0 <= value <= 5):
                raise ValueError(f"Invalid response value for {key}: {value}. Must be between 0 and 5.")
        return responses


class MajorData(BaseModel):
    major_name: str
    schools: List[str]


class CareerData(BaseModel):
    career_name: str
    description: Optional[str] = None
    majors: List[MajorData]


class ChartData(BaseModel):
    label: str
    score: float


class DimensionDescription(BaseModel):
    dimension_name: str
    description: str
    image_url: Optional[str]


class InterestAssessmentResponse(BaseModel):
    user_uuid: str
    test_uuid: str
    test_name: str
    holland_code: str
    type_name: str
    description: str
    key_traits: List[str]
    career_path: List[CareerData]
    chart_data: List[ChartData]
    dimension_descriptions: List[DimensionDescription]


class InterestAssessmentResponseWithBase(BaseResponse):
    payload: InterestAssessmentResponse