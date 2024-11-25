from pydantic import BaseModel, Field, validator
from typing import Dict





class InterestAssessmentResponseDto(BaseModel):
    user_id: str
    holland_code: str
    type_name: str
    description: str
    key_traits: str
    career_path: list
    probabilistic_scores: Dict[str, float]


class PersonalityAssessmentInputDto(BaseModel):
    responses: Dict[str, int] = Field(
        ..., description="Mapping of personality question keys to user responses (1-5 scale)."
    )

    @validator("responses")
    def validate_responses(cls, responses):
        valid_prefixes = [
            "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
            "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"
        ]
        for key in responses.keys():
            if not any(key.startswith(prefix) and key[-1].isdigit() for prefix in valid_prefixes):
                raise ValueError(f"Invalid question key format: {key}")
        return responses


class PersonalityAssessmentResponseDto(BaseModel):
    personality_type: str
    description: str
    strengths: list
    weaknesses: list


