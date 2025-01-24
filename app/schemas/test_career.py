from typing import List, Optional
from pydantic import BaseModel


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
    career_name: str
    description: Optional[str] = None
    categories: List[CategoryWithResponsibilities]
    majors: List[MajorWithSchools]
