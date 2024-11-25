from pydantic import BaseModel, validator, Field
from typing import List, Dict


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


class ChartData(BaseModel):
    label: str
    score: float


class DimensionDescription(BaseModel):
    dimension_name: str
    description: str


class InterestAssessmentResponse(BaseModel):
    user_id: str
    holland_code: str
    type_name: str
    description: str
    key_traits: List[str]
    career_path: List[str]
    chart_data: List[ChartData]
    dimension_descriptions: List[DimensionDescription]
