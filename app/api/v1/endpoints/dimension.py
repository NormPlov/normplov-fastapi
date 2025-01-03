from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.dimension import load_all_dimensions
from app.dependencies import get_current_user_data
from app.schemas.payload import BaseResponse

dimension_router = APIRouter()


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