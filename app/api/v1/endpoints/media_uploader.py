from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.payload import BaseResponse
from app.services.media_uploader import upload_image
from datetime import datetime

media_uploader_router = APIRouter()


@media_uploader_router.post("/upload-image", response_model=BaseResponse)
async def upload_image_route(file: UploadFile = File(...)):
    try:
        file_data = await upload_image(file)

        current_date = datetime.utcnow().strftime("%d-%B-%Y")

        return BaseResponse(
            date=current_date,
            status=200,
            payload={
                "file_url": file_data["file_url"],
                "file_size": file_data["file_size"],
                "file_type": file_data["file_type"]
            },
            message="Image uploaded successfully"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error uploading image")
