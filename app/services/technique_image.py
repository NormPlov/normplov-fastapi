import os
import shutil
from uuid import uuid4
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.concurrency import run_in_threadpool

from app.models.learning_style_study_technique import LearningStyleStudyTechnique
from app.models.learning_style_technique_image import LearningStyleTechniqueImage
from app.core.config import settings
from app.schemas.technique_image import LearningStyleTechniqueImageResponse
from app.schemas.payload import BaseResponse
from datetime import date


async def upload_learning_style_image(
    technique_uuid: str,
    file: UploadFile,
    db: AsyncSession
) -> LearningStyleTechniqueImageResponse:
    try:
        technique_stmt = select(LearningStyleStudyTechnique).where(
            LearningStyleStudyTechnique.uuid == technique_uuid,
            LearningStyleStudyTechnique.is_deleted == False
        )
        result = await db.execute(technique_stmt)
        technique = result.scalars().first()

        if not technique:
            raise HTTPException(status_code=404, detail="Learning Style Technique not found.")

        upload_folder = settings.LEARNING_STYLE_UPLOAD_FOLDER
        await run_in_threadpool(os.makedirs, upload_folder, exist_ok=True)

        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in [".png", ".jpg", ".jpeg", ".gif"]:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PNG, JPG, JPEG, or GIF.")

        new_filename = f"{uuid4()}{file_extension}"
        file_path = os.path.join(upload_folder, new_filename)

        async with file.file as file_stream:
            await run_in_threadpool(save_file, file_stream, file_path)

        image = LearningStyleTechniqueImage(
            uuid=str(uuid4()),
            learning_style_technique_id=technique.id,
            file_name=file.filename,
            file_url=f"/uploads/learning_style/{new_filename}",
            file_type=file.content_type,
        )
        db.add(image)
        await db.commit()

        return LearningStyleTechniqueImageResponse(
            uuid=image.uuid,
            file_name=image.file_name,
            file_url=image.file_url,
            file_type=image.file_type,
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while uploading the image: {str(e)}")


def save_file(file_stream, file_path):
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file_stream, buffer)


async def update_learning_style_image(
    image_uuid: str,
    file: UploadFile,
    db: AsyncSession
) -> BaseResponse:
    try:
        image_stmt = select(LearningStyleTechniqueImage).where(
            LearningStyleTechniqueImage.uuid == image_uuid,
            LearningStyleTechniqueImage.is_deleted == False
        )
        result = await db.execute(image_stmt)
        image = result.scalars().first()

        if not image:
            raise HTTPException(status_code=404, detail="Image not found.")

        upload_folder = settings.LEARNING_STYLE_UPLOAD_FOLDER
        os.makedirs(upload_folder, exist_ok=True)

        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in [".png", ".jpg", ".jpeg", ".gif"]:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PNG, JPG, JPEG, or GIF.")

        old_file_path = os.path.join(upload_folder, os.path.basename(image.file_url))
        if os.path.exists(old_file_path):
            os.remove(old_file_path)

        new_filename = f"{uuid4()}{file_extension}"
        file_path = os.path.join(upload_folder, new_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        image.file_name = file.filename
        image.file_url = f"/uploads/learning_style/{new_filename}"
        image.file_type = file.content_type
        await db.commit()

        return BaseResponse(
            date=date.today(),
            status=200,
            payload={
                "image_uuid": image.uuid,
                "file_name": image.file_name,
                "file_url": image.file_url,
                "file_type": image.file_type,
            },
            message="Image updated successfully.",
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while updating the image: {str(e)}")


async def load_all_learning_style_images(db: AsyncSession) -> BaseResponse:
    try:
        image_stmt = select(LearningStyleTechniqueImage).where(
            LearningStyleTechniqueImage.is_deleted == False
        )
        result = await db.execute(image_stmt)
        images = result.scalars().all()

        payload = [
            {
                "uuid": image.uuid,
                "file_name": image.file_name,
                "file_url": image.file_url,
                "file_type": image.file_type,
            }
            for image in images
        ]

        return BaseResponse(
            date=date.today(),
            status=200,
            payload=payload,
            message="Images fetched successfully.",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching images: {str(e)}")


async def delete_learning_style_image(image_uuid: str, db: AsyncSession) -> BaseResponse:
    try:
        image_stmt = select(LearningStyleTechniqueImage).where(
            LearningStyleTechniqueImage.uuid == image_uuid,
            LearningStyleTechniqueImage.is_deleted == False
        )
        result = await db.execute(image_stmt)
        image = result.scalars().first()

        if not image:
            raise HTTPException(status_code=404, detail="Image not found.")

        image.is_deleted = True
        file_path = os.path.join(settings.LEARNING_STYLE_UPLOAD_FOLDER, os.path.basename(image.file_url))
        if os.path.exists(file_path):
            os.remove(file_path)

        await db.commit()

        return BaseResponse(
            date=date.today(),
            status=200,
            payload={"image_uuid": image_uuid},
            message="Image deleted successfully.",
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while deleting the image: {str(e)}")
