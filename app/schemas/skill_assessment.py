from pydantic import BaseModel, Field, validator
from typing import Dict, List
from typing import Optional


class SkillAssessmentInput(BaseModel):
    responses: Dict[str, float] = Field(
        ..., description="Mapping of skill names to their scores."
    )
    test_uuid: Optional[str] = Field(
        None, description="Optional UUID for linking to an existing test."
    )

    @validator("responses")
    def validate_scores(cls, responses):
        if not responses:
            raise ValueError("Responses cannot be empty.")
        for skill, value in responses.items():
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"Invalid score for {skill}: {value}. Must be non-negative.")
        return responses


class MajorWithSchools(BaseModel):
    major_name: str
    schools: List[str]


class CareerWithMajors(BaseModel):
    career_name: str
    majors: List[MajorWithSchools]


class SkillGroupedByLevel(BaseModel):
    skill: str
    description: str


class SkillAssessmentResponse(BaseModel):
    category_percentages: Dict[str, float]
    skills_grouped: Dict[str, List[SkillGroupedByLevel]]
    strong_careers: List[CareerWithMajors]