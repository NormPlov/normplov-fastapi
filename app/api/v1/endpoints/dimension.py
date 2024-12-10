from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.dimension import UploadDimensionImageResponse
from app.services.dimension import upload_dimension_image, load_all_dimensions
from app.dependencies import is_admin_user, get_current_user_data
from app.schemas.payload import BaseResponse

dimension_router = APIRouter()


@dimension_router.post(
    "/upload-image/{dimension_uuid}",
    response_model=BaseResponse,
    summary="Upload an image for a dimension (Admin Only)",
)
async def upload_dimension_image_route(
    dimension_uuid: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(is_admin_user),
):
    try:
        result = await upload_dimension_image(db=db, dimension_uuid=dimension_uuid, file=file)
        return BaseResponse(
            date=datetime.utcnow(),
            status=200,
            payload=UploadDimensionImageResponse(**result),
            message="Image uploaded successfully",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@dimension_router.get(
    "/",
    response_model=BaseResponse,
    summary="Load all dimensions (Authenticated Users)",
)
async def load_all_dimensions_route(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        dimensions = await load_all_dimensions(db)
        return BaseResponse(
            date=datetime.utcnow(),
            status=200,
            payload=dimensions,
            message="Dimensions loaded successfully",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")