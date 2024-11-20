from pydantic import BaseModel, Field, validator
from typing import Dict

class LearningStyleInput(BaseModel):
    answers: Dict[str, int] = Field(..., description="Mapping of question keys to answers")

    @validator("answers")
    def validate_keys(cls, answers):
        for key in answers.keys():
            if not key.startswith("Q") or "_" not in key:
                raise ValueError(f"Invalid question key format: {key}")
        return answers


class SkillInput(BaseModel):
    scores: Dict[str, float] = Field(..., description="Mapping of skill names to scores")

    class Config:
        json_schema_extra = {
            "example": {
                "scores": {
                    "Complex Problem Solving": 4.2,
                    "Critical Thinking Score": 3.5,
                    "Mathematics Score": 4.8,
                    "Science Score": 3.2,
                    "Learning Strategy Score": 3.9,
                    "Monitoring Score": 4.1,
                    "Active Listening Score": 4.0,
                    "Social Perceptiveness Score": 2.5,
                    "Judgment and Decision Making Score": 4.7,
                    "Instructing Score": 3.0,
                    "Active Learning Score": 3.8,
                    "Time Management Score": 2.0,
                    "Writing Score": 1.8,
                    "Speaking Score": 4.6,
                    "Reading Comprehension Score": 1.2
                }
            }
        }
