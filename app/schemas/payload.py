from pydantic import BaseModel
from typing import Any
from datetime import date

class BaseResponse(BaseModel):
    date: date
    status: int
    payload: Any
    message: str
