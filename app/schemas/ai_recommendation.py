from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AIRecommendationCreate(BaseModel):
    query: str = Field(..., description="User's query or question")

    class Config:
        schema_extra = {
            "example": {
                "query": "How can I improve my communication skills?"
            }
        }

class AIRecommendationResponse(BaseModel):
    id: int
    uuid: str
    user_id: int
    query: str
    recommendation: str
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True
