from pydantic import BaseModel, Field
from typing import Dict, List


class PersonalityAssessmentInput(BaseModel):
    responses: Dict[str, int] = Field(
        ..., description="Key-value pairs of question identifiers and user responses."
    )


class MajorData(BaseModel):
    major_name: str
    schools: List[str]


class CareerData(BaseModel):
    career_name: str
    majors: List[MajorData]


class PersonalityTypeDetails(BaseModel):
    name: str
    title: str
    description: str


class DimensionScore(BaseModel):
    dimension_name: str
    score: float


class PersonalityTraits(BaseModel):
    positive: List[str]
    negative: List[str]


class PersonalityAssessmentResponse(BaseModel):
    user_uuid: str
    personality_type: PersonalityTypeDetails
    dimensions: List[DimensionScore]
    traits: PersonalityTraits
    strengths: List[str]
    weaknesses: List[str]
    career_recommendations: List[CareerData]