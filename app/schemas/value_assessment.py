from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class ValueAssessmentInput(BaseModel):
    responses: Dict[str, int] = Field(
        ..., description="User responses to value assessment questions (1-5 scale)."
    )


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


class ValueCategoryDetails(BaseModel):
    name: str
    definition: str
    characteristics: str
    percentage: str


class KeyImprovement(BaseModel):
    category: str
    improvements: List[str]


class ValueAssessmentResponse(BaseModel):
    user_uuid: str
    test_uuid: str
    test_name: str
    chart_data: List[ChartData]
    value_details: List[ValueCategoryDetails]
    career_recommendations: List[CareerData]
    key_improvements: List[KeyImprovement] = Field(
        default=[],
        description="Key improvements for categories with low scores (<2)."
    )
