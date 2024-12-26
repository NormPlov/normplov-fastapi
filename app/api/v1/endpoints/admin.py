import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.payload import BaseResponse
from app.services.admin import fetch_metrics, get_admin_user_responses
from app.core.database import get_db
from app.models import User
from app.dependencies import is_admin_user
from datetime import datetime

admin_router = APIRouter()
logger = logging.getLogger(__name__)


@admin_router.get(
    "/responses/{test_uuid}",
    summary="Get user responses by test UUID (Admin only)",
    response_model=BaseResponse,
    tags=["Admin Responses"],
)
async def get_user_responses_by_test_uuid(
    test_uuid: str,
    user_id: Optional[int] = Query(None, description="Filter by specific user ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
):
    try:
        # Fetch responses
        responses = await get_admin_user_responses(db, test_uuid, user_id)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=200,
            message="User responses retrieved successfully.",
            payload=responses,
        )
    except HTTPException as http_exc:
        logger.error(f"HTTPException while fetching responses for test {test_uuid}: {http_exc.detail}")
        raise http_exc
    except AttributeError as attr_err:
        logger.error(f"AttributeError while fetching responses for test {test_uuid}: {attr_err}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing the request.",
        )
    except Exception as e:
        logger.error(f"Unexpected error while fetching responses for test {test_uuid}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving user responses.",
        )


@admin_router.get("/metrics", response_model=BaseResponse)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(is_admin_user),
    year: int = Query(None, description="Filter data by year"),
    month: int = Query(None, description="Filter data by month"),
    week: int = Query(None, description="Filter data by week")
):
    metrics = await fetch_metrics(db, year=year, month=month, week=week)
    return BaseResponse(
        date=datetime.utcnow(),
        status=200,
        message="Metrics retrieved successfully.",
        payload=metrics
    )