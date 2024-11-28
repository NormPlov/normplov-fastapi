from pydantic import BaseModel, validator
from typing import Any
from datetime import date


class BaseResponse(BaseModel):
    date: str
    status: int
    payload: Any
    message: str

    @validator("date", pre=True)
    def format_date(cls, value):
        if isinstance(value, date):
            return value.strftime("%d-%B-%Y")
        return value
