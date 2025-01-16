from typing import List, Optional
from pydantic import BaseModel


class MajorData(BaseModel):
    major_name: str
    schools: List[str]


class CategoryWithResponsibilities(BaseModel):
    category_name: str
    responsibilities: List[str]


class CareerData(BaseModel):
    career_name: str
    description: Optional[str] = None
    categories: List[CategoryWithResponsibilities]
    majors: List[MajorData]
