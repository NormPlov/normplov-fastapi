import uuid

from datetime import datetime
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_current_user_data
from app.schemas.job import JobListingResponse
from app.schemas.payload import BaseResponse
from app.services.bookmark import add_job_to_bookmark_service, get_user_bookmarked_jobs_service, unbookmark_job_service
from app.models.user import User
from app.core.database import get_db
from app.utils.pagination import paginate_results

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
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of jobs per page"),
    current_user: User = Depends(get_current_user_data),
    db: AsyncSession = Depends(get_db),
):
    try:
        bookmarked_jobs = await get_user_bookmarked_jobs_service(current_user, db)

        paginated_result = paginate_results(bookmarked_jobs, page=page, page_size=page_size)

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message="Bookmarked jobs retrieved successfully",
            payload=paginated_result,
        )
    except HTTPException as e:
        if e.status_code == 404:
            return BaseResponse(
                date=datetime.utcnow().strftime("%d-%B-%Y"),
                status=status.HTTP_404_NOT_FOUND,
                message="No bookmarked jobs found for this user.",
                payload={
                    "items": [],
                    "metadata": {
                        "page": page,
                        "page_size": page_size,
                        "total_items": 0,
                        "total_pages": 0,
                    },
                },
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving bookmarked jobs: {str(e)}",
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