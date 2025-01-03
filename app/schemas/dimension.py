from typing import Optional
from pydantic import BaseModel


class DimensionResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str]
    image: Optional[str]
    created_at: str
    updated_at: Optional[str]