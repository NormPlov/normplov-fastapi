from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.province import load_provinces
from app.schemas.payload import BaseResponse
from app.dependencies import get_current_user_data

province_router = APIRouter()


@province_router.get(
    "/",
    response_model=BaseResponse,
    summary="Load provinces",
    description="Fetch the list of provinces.",
    tags=["Provinces"],
)
async def get_provinces_route(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access. Please log in to access this resource."
        )

    return await load_provinces(db)
