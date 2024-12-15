import os
from fastapi import HTTPException, UploadFile
from app.core.config import settings


def validate_file_extension(filename: str) -> bool:

    return filename.lower().endswith(tuple(settings.ALLOWED_EXTENSIONS))


def validate_file_size(file: UploadFile) -> None:

    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum limit.")
