from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional


class LearningStyleInput(BaseModel):
    test_uuid: Optional[str] = Field(
        None, description="Optional test UUID. A new test will be created if not provided."
    )
    responses: Dict[str, int] = Field(
        ...,
        description="Mapping of learning style question keys to answers (1-5 scale).",
    )

    @validator("responses")
    def validate_responses(cls, responses):
        if not responses:
            raise ValueError("Responses cannot be empty.")
        for question, value in responses.items():
            if not isinstance(value, int) or value < 1 or value > 5:
                raise ValueError(f"Invalid response for {question}: {value}. Must be an integer between 1 and 5.")
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
    categories: List[CategoryWithResponsibilities] = Field(default_factory=list)
    majors: List[MajorWithSchools] = Field(default_factory=list)


class LearningStyleChart(BaseModel):
    labels: List[str]
    values: List[float]


class DimensionDetail(BaseModel):
    dimension_name: str
    dimension_description: str
    level: int


class Technique(BaseModel):
    technique_name: str
    category: str
    description: str
    image_url: Optional[str] = Field(None, description="URL of the technique's image")


class LearningStyleResponse(BaseModel):
    user_uuid: str
    test_uuid: str
    test_name: str
    learning_style: str
    probability: float
    details: Dict[str, float]
    chart: LearningStyleChart
    dimensions: List[DimensionDetail]
    recommended_techniques: List[Technique]
    related_careers: List[CareerData]
