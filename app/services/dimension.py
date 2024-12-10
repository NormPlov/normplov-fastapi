import os

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.dimension import Dimension
from app.core.config import settings
from app.schemas.dimension import DimensionResponse


async def upload_dimension_image(db: AsyncSession, dimension_uuid: str, file: UploadFile):
    try:
        dimension_query = select(Dimension).where(
            Dimension.uuid == dimension_uuid,
            Dimension.is_deleted == False
        )
        dimension_result = await db.execute(dimension_query)
        dimension = dimension_result.scalars().first()

        if not dimension:
            raise HTTPException(status_code=404, detail="Dimension not found.")

        upload_folder = os.path.join(settings.BASE_UPLOAD_FOLDER, "dimension")
        os.makedirs(upload_folder, exist_ok=True)

        file_name = f"{dimension.uuid}_{file.filename}"
        file_path = os.path.join(upload_folder, file_name)

        try:
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

        dimension.image = os.path.join("dimension", file_name)
        await db.commit()
        await db.refresh(dimension)

        return {
            "dimension_uuid": dimension.uuid,
            "image_url": f"/{settings.BASE_UPLOAD_FOLDER}/dimension/{file_name}",
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


async def load_all_dimensions(db: AsyncSession):
    try:
        stmt = select(Dimension).where(Dimension.is_deleted == False)
        result = await db.execute(stmt)
        dimensions = result.scalars().all()

        if not dimensions:
            return []

        return [
            DimensionResponse(
                uuid=dimension.uuid,
                name=dimension.name,
                description=dimension.description,
                image=dimension.image,
                created_at=dimension.created_at.strftime("%d-%B-%Y"),
                updated_at=dimension.updated_at.strftime("%d-%B-%Y") if dimension.updated_at else None,
            )
            for dimension in dimensions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dimensions: {str(e)}")