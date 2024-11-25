from pydantic import BaseModel, Field, validator
from typing import Dict, List


class SkillAssessmentInput(BaseModel):
    scores: Dict[str, float] = Field(
        ..., description="Mapping of skill names to their scores."
    )

    @validator("scores")
    def validate_scores(cls, scores):
        if not scores:
            raise ValueError("Scores cannot be empty.")
        for skill, value in scores.items():
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"Invalid score for {skill}: {value}. Must be non-negative.")
        return scores


class SkillGroupedByLevel(BaseModel):
    skill: str
    description: str


class SkillAssessmentResponse(BaseModel):
    category_percentages: Dict[str, float]
    skills_grouped: Dict[str, List[SkillGroupedByLevel]]
    strong_careers: List[Dict[str, str]]