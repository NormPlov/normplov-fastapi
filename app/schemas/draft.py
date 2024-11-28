from pydantic import BaseModel, Field
from typing import Any, Dict


class DraftCreateUpdateInput(BaseModel):
    assessment_type_uuid: str = Field(..., description="UUID of the assessment type.")
    response_data: Dict[str, Any] = Field(
        ..., description="Data representing the draft responses."
    )

    model_config = {
        "arbitrary_types_allowed": True
    }


class DraftResponse(BaseModel):
    draft_uuid: str
    test_uuid: str
    response_data: Any
    message: str


class DraftListResponse(BaseModel):
    drafts: list[DraftResponse]
