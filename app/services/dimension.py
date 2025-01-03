from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.dimension import Dimension
from app.schemas.dimension import DimensionResponse


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