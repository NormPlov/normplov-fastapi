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
    response_data: Dict = Field(...)
    test_uuid: Optional[str] = Field(None)


class SaveDraftResponse(BaseModel):
    uuid: str = Field(...)
    message: str = Field(...)
    draft_name: str = Field(...)



