from pydantic import BaseModel
from typing import Dict, Optional
from app.schemas.interest_assessment import InterestAssessmentResponse
from app.schemas.learning_style_assessment import LearningStyleResponse
from app.schemas.personality_assessment import PersonalityAssessmentResponse
from app.schemas.skill_assessment import SkillAssessmentResponse
from app.schemas.value_assessment import ValueAssessmentResponse


class LearningStyleInput(BaseModel):
    responses: Dict[str, int]


class SkillAssessmentInput(BaseModel):
    responses: Dict[str, int]


class PersonalityAssessmentInput(BaseModel):
    responses: Dict[str, int]


class InterestAssessmentInput(BaseModel):
    responses: Dict[str, int]


class ValueAssessmentInput(BaseModel):
    responses: Dict[str, int]


class AllAssessmentsInput(BaseModel):
    learning_style: LearningStyleInput
    skill: SkillAssessmentInput
    personality: PersonalityAssessmentInput
    interest: InterestAssessmentInput
    value: ValueAssessmentInput


class AllAssessmentsResponse(BaseModel):
    learning_style: Optional[LearningStyleResponse]
    skill: Optional[SkillAssessmentResponse]
    personality: Optional[PersonalityAssessmentResponse]
    interest: Optional[InterestAssessmentResponse]
    value: Optional[ValueAssessmentResponse]
