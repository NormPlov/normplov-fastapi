from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional


class LearningStyleInput(BaseModel):
    test_uuid: Optional[str] = Field(
        None, description="Optional test UUID. A new test will be created if not provided."
    )
    responses: Dict[str, int] = Field(
        ...,
        description="Mapping of learning style question keys to answers (1-5 scale).",
    )

    @validator("responses")
    def validate_responses(cls, responses):
        if not responses:
            raise ValueError("Responses cannot be empty.")
        for question, value in responses.items():
            if not isinstance(value, int) or value < 1 or value > 5:
                raise ValueError(f"Invalid response for {question}: {value}. Must be an integer between 1 and 5.")
        return responses


class Technique(BaseModel):
    technique_name: str
    category: str
    description: str


class DimensionDetail(BaseModel):
    dimension_name: str
    dimension_description: str
    techniques: List[Technique]


class LearningStyleChart(BaseModel):
    labels: List[str]
    values: List[float]


class LearningStyleResponse(BaseModel):
    user_id: str
    learning_style: str
    probability: float
    details: Dict[str, float]
    chart: LearningStyleChart
    dimensions: List[DimensionDetail]
    related_careers: List[Dict[str, str]]
