import uuid

from datetime import datetime
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_current_user_data
from app.exceptions.formatters import format_http_exception
from app.schemas.payload import BaseResponse
from app.services.bookmark import add_job_to_bookmark_service, get_user_bookmarked_jobs_service, unbookmark_job_service
from app.models.user import User
from app.core.database import get_db

bookmark_router = APIRouter()


@bookmark_router.delete("/{bookmark_uuid}", response_model=BaseResponse, status_code=status.HTTP_200_OK)
async def unbookmark_job_route(
    bookmark_uuid: uuid.UUID,
    current_user: User = Depends(get_current_user_data),
    db: AsyncSession = Depends(get_db)
):
    response = await unbookmark_job_service(current_user, bookmark_uuid, db)
    return response


@bookmark_router.get("/", response_model=BaseResponse, status_code=status.HTTP_200_OK)
async def get_bookmarked_jobs(
    current_user: User = Depends(get_current_user_data),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, description="Page number for pagination", ge=1),
    page_size: int = Query(10, description="Number of items per page", ge=1, le=100),
):
    try:
        bookmarked_jobs = await get_user_bookmarked_jobs_service(
            current_user, db, page, page_size
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message="🎉 Bookmarked jobs retrieved successfully.",
            payload=bookmarked_jobs,
        )
    except HTTPException as e:
        # Handle 404 errors explicitly
        if e.status_code == status.HTTP_404_NOT_FOUND:
            return BaseResponse(
                date=datetime.utcnow().strftime("%d-%B-%Y"),
                status=status.HTTP_404_NOT_FOUND,
                message=e.detail["message"],
                payload={"items": [], "metadata": {"page": page, "page_size": page_size, "total_items": 0, "total_pages": 0}},
            )
        # Other exceptions with formatted error messages
        raise format_http_exception(
            status_code=e.status_code,
            message="❌ An error occurred while retrieving bookmarked jobs.",
            details=e.detail,
        )


@bookmark_router.post("/{job_uuid}", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def add_job_to_bookmark(
    job_uuid: uuid.UUID,
    current_user: User = Depends(get_current_user_data),
    db: AsyncSession = Depends(get_db)
):
    response = await add_job_to_bookmark_service(job_uuid, current_user, db)
    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=201,
        message=response["message"],
        payload={"uuid": response["uuid"]}
    )