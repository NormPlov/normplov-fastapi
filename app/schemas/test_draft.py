from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class TestDraftBase(BaseModel):
    assessment_type_uuid: Optional[str] = Field(None, description="UUID of the assessment type")
    draft_data: Any = Field({}, description="Data of the draft")
    is_completed: Optional[bool] = Field(False, description="Whether the draft is completed")


class TestDraftCreate(TestDraftBase):
    pass


class TestDraftUpdate(BaseModel):
    draft_data: Optional[Any] = Field(None, description="Updated data of the draft")
    is_completed: Optional[bool] = Field(None, description="Update completion status")


class TestDraftResponse(TestDraftBase):
    uuid: str
    user_uuid: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
