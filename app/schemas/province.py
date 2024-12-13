from pydantic import BaseModel, Field
from datetime import datetime
from typing import List


class ProvinceResponse(BaseModel):
    uuid: str = Field(..., description="The UUID of the province.")
    name: str = Field(..., description="The name of the province.")
    created_at: datetime = Field(..., description="The date and time when the province was created.")
    updated_at: datetime = Field(..., description="The date and time when the province was last updated.")

    class Config:
        orm_mode = True


class ProvinceListResponse(BaseModel):
    provinces: List[ProvinceResponse]
