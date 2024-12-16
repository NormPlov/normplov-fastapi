from pydantic import BaseModel, Field
from typing import Optional, List

from app.schemas.payload import BaseResponse


class CreateFeedbackRequest(BaseModel):
    feedback: str = Field(..., min_length=1, max_length=500, description="Feedback content")
    user_test_uuid: str = Field(..., description="UUID of the user test")

    class Config:
        orm_mode = True


class FeedbackDetails(BaseModel):
    feedback_uuid: str
    username: str
    email: str
    avatar: str
    feedback: str
    is_deleted: bool
    is_promoted: bool
    created_at: str

    class Config:
        orm_mode = True


class AllFeedbacksResponse(BaseResponse):
    payload: List[FeedbackDetails]


class CreateFeedbackResponse(BaseModel):
    date: str
    status: int
    message: str
    payload: Optional[dict] = None


class PromotedFeedbackDetails(BaseModel):
    feedback_uuid: str
    username: str
    email: str
    avatar: str
    feedback: str
    created_at: str

    class Config:
        orm_mode = True


class PromotedFeedbacksResponse(BaseModel):
    date: str
    status: int
    message: str
    payload: List[PromotedFeedbackDetails]
