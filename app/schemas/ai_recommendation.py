from pydantic import BaseModel, Field


class ContinueConversationRequest(BaseModel):
    new_query: str


class AIRecommendationCreate(BaseModel):
    query: str = Field(..., description="User's query or question")

    class Config:
        schema_extra = {
            "example": {
                "query": "How can I improve my communication skills?"
            }
        }


class RenameAIRecommendationRequest(BaseModel):
    new_title: str


class AIRecommendationResponse(BaseModel):
    uuid: str
    user_uuid: str
    query: str
    recommendation: str
    chat_title: str
    created_at: str
    updated_at: str | None = None

    class Config:
        orm_mode = True
