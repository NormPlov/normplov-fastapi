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


class SkillGroupedByLevel(BaseModel):
    skill: str
    description: str


class SkillAssessmentResponse(BaseModel):
    skills_grouped: Dict[str, List[SkillGroupedByLevel]]


class ChartData(BaseModel):
    label: str
    score: float


class ValueAssessmentResponse(BaseModel):
    chart_data: List[ChartData]


class AllAssessmentsResponse(BaseModel):
    skill: Optional[SkillAssessmentResponse] = None
    interest: Optional[InterestAssessmentResponse] = None
    learning_style: Optional[LearningStyleResponse] = None
    value: Optional[ValueAssessmentResponse]
    personality: Optional[PersonalityAssessmentResponse] = None


# Request Body for Final Assessment
class PredictCareersRequest(BaseModel):
    test_uuids: List[str]