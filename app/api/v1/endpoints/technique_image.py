from fastapi import APIRouter, HTTPException, Depends, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.technique_image import (
    upload_learning_style_image,
    update_learning_style_image,
    delete_learning_style_image,
    load_all_learning_style_images,
)
from app.schemas.technique_image import LearningStyleTechniqueImageResponse
from app.schemas.payload import BaseResponse
from app.models.user import User
from app.dependencies import get_current_user_data


learning_style_image_router = APIRouter()


def is_admin(current_user: User):
    if not hasattr(current_user, "roles") or "ADMIN" not in {role.name.upper() for role in current_user.roles}:
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only")


@learning_style_image_router.post(
    "/upload-learning-style-image",
    response_model=LearningStyleTechniqueImageResponse,
    summary="Upload an image for a learning style technique"
)
async def upload_learning_style_image_route(
    technique_uuid: str = Form(...),
    file: UploadFile = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        is_admin(current_user)
        return await upload_learning_style_image(technique_uuid, file, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@learning_style_image_router.put(
    "/update-learning-style-image/{image_uuid}",
    response_model=BaseResponse,
    summary="Update an image for a learning style technique"
)
async def update_learning_style_image_route(
    image_uuid: str,
    file: UploadFile = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        is_admin(current_user)
        return await update_learning_style_image(image_uuid, file, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@learning_style_image_router.get(
    "/load-all-learning-style-images",
    response_model=BaseResponse,
    summary="Load all images for learning style techniques"
)
async def load_all_learning_style_images_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        return await load_all_learning_style_images(db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@learning_style_image_router.delete(
    "/delete-learning-style-image/{image_uuid}",
    response_model=BaseResponse,
    summary="Delete an image for a learning style technique"
)
async def delete_learning_style_image_route(
    image_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    """Delete a learning style image."""
    try:
        is_admin(current_user)
        return await delete_learning_style_image(image_uuid, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
