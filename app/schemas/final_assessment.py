from pydantic import BaseModel
from typing import Dict, Optional, List


class InterestAssessmentResponse(BaseModel):
    type_name: str


class LearningStyleResponse(BaseModel):
    learning_style: str


class PersonalityTypeDetails(BaseModel):
    name: str
    title: str
    description: str


class PersonalityAssessmentResponse(BaseModel):
    personality_type: PersonalityTypeDetails


class SkillAssessmentResponse(BaseModel):
    top_category: str


class ValueAssessmentResponse(BaseModel):
    chart_data: Dict[str, List[int]]


class AllAssessmentsResponse(BaseModel):
    learning_style: Optional[LearningStyleResponse] = None
    skill: Optional[SkillAssessmentResponse] = None
    personality: Optional[PersonalityAssessmentResponse] = None
    interest: Optional[InterestAssessmentResponse] = None
    value: Optional[ValueAssessmentResponse]
