from datetime import datetime

from pydantic import BaseModel, Field
from typing import Dict, Optional


class DraftItem(BaseModel):
    uuid: str = Field(...)
    draft_name: str = Field(...)
    assessment_name: str = Field(...)
    created_at: str = Field(...)
    updated_at: Optional[str] = Field(None)
    response_data: Dict = Field(...)


class SaveDraftRequest(BaseModel):
    response_data: Dict = Field(..., description="The draft response data as a dictionary.")


class DraftResponse(BaseModel):
    draft_uuid: str
    draft_name: str
    response_data: Dict
    created_at: datetime
    updated_at: Optional[datetime]



