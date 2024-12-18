from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.payload import BaseResponse
from app.services.admin_metrics import fetch_metrics
from app.core.database import get_db
from app.models import User
from app.dependencies import is_admin_user
from datetime import datetime

admin_router = APIRouter()


@admin_router.get("/metrics", response_model=BaseResponse)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(is_admin_user)
):
    metrics = await fetch_metrics(db)

    return BaseResponse(
        date=datetime.utcnow(),
        status=200,
        message="Metrics retrieved successfully.",
        payload=metrics
    )
