from pydantic import BaseModel, Field, validator
from typing import Dict, List
from typing import Optional


class SkillAssessmentInput(BaseModel):
    responses: Dict[str, float] = Field(
        ..., description="Mapping of skill names to their scores as floating-point numbers."
    )

    @validator("responses")
    def validate_scores(cls, responses):
        if not responses:
            raise ValueError("Responses cannot be empty.")
        for skill, value in responses.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Invalid score for {skill}: {value}. Must be a number.")
            if value < 0:
                raise ValueError(f"Score for {skill} must be non-negative.")
        return responses


class SchoolData(BaseModel):
    school_uuid: str
    school_name: str


class MajorWithSchools(BaseModel):
    major_name: str
    schools: List[SchoolData]


class CategoryWithResponsibilities(BaseModel):
    category_name: str
    responsibilities: List[str]


class CareerData(BaseModel):
    career_uuid: Optional[str] = None
    career_name: str
    description: Optional[str] = None
    categories: List[CategoryWithResponsibilities]
    majors: List[MajorWithSchools]


class SkillGroupedByLevel(BaseModel):
    skill: str
    description: str


class SkillAssessmentResponse(BaseModel):
    user_uuid: str
    test_uuid: str
    test_name: str
    top_category: Dict[str, str]
    category_percentages: Dict[str, float]
    skills_grouped: Dict[str, List[SkillGroupedByLevel]]
    strong_careers: List[CareerData]