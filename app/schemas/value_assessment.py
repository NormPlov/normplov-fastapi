from pydantic import BaseModel, Field
from typing import List, Dict


class ValueAssessmentInput(BaseModel):
    responses: Dict[str, int] = Field(
        ..., description="User responses to value assessment questions (1-5 scale)."
    )


class ChartData(BaseModel):
    label: str
    score: float


class ValueCategoryDetails(BaseModel):
    name: str
    definition: str
    characteristics: str
    percentage: str


class ValueAssessmentResponse(BaseModel):
    user_id: str
    chart_data: List[ChartData]
    value_details: List[ValueCategoryDetails]
    career_recommendations: List[str]
