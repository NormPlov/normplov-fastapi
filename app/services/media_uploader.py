import os
import uuid
import logging

from fastapi import UploadFile, HTTPException
from app.core.config import settings
from app.utils.file import validate_file_extension, validate_file_size

logger = logging.getLogger(__name__)


async def upload_image(file: UploadFile) -> dict:
    try:
        if not validate_file_extension(file.filename):
            raise HTTPException(status_code=400, detail="Invalid file type. Allowed types are: jpg, png, jpeg.")

        validate_file_size(file)

        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"

        upload_dir = settings.BASE_UPLOAD_FOLDER
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, unique_filename)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        file_size = os.path.getsize(file_path)

        file_type = file.content_type

        file_url = f"{upload_dir}/{unique_filename}"

        return {
            "file_url": file_url,
            "file_size": file_size,
            "file_type": file_type
        }

    except HTTPException as e:
        logger.error(f"HTTPException occurred: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Error occurred while uploading the file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while uploading the file: {str(e)}")