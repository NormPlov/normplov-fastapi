from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class PersonalityAssessmentInput(BaseModel):
    responses: Dict[str, int] = Field(
        ..., description="Key-value pairs of question identifiers and user responses."
    )


class MajorData(BaseModel):
    major_name: str
    schools: List[str]


class CategoryWithResponsibilities(BaseModel):
    category_name: str
    responsibilities: List[str]


class CareerData(BaseModel):
    career_uuid: Optional[str] = None
    career_name: str
    description: Optional[str] = None
    categories: List[CategoryWithResponsibilities] = Field(default_factory=list)
    majors: List[MajorData] = Field(default_factory=list)


class PersonalityTypeDetails(BaseModel):
    name: str
    title: str
    description: str


class DimensionScore(BaseModel):
    dimension_name: str
    score: float
    percentage: str


# class PersonalityTraits(BaseModel):
#     positive: List[str]
#     negative: List[str]
class PersonalityCharacteristics(BaseModel):
    name: str
    description: str


class PersonalityAssessmentResponse(BaseModel):
    user_uuid: str
    test_uuid: str
    test_name: str
    personality_type: PersonalityTypeDetails
    dimensions: List[DimensionScore]
    # traits: PersonalityTraits
    traits: List[PersonalityCharacteristics]
    strengths: List[str]
    weaknesses: List[str]
    career_recommendations: List[CareerData] = Field(default_factory=list)