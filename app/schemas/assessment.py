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
