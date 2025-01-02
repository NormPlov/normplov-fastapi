from pydantic import BaseModel
from typing import Dict


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
