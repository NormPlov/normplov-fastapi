from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    file_url: str

    class Config:
        orm_mode = True
