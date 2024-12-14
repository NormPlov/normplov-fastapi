from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import is_admin_user
from app.exceptions.formatters import format_http_exception
from app.schemas.payload import BaseResponse
from app.services.job import create_job, update_job, load_all_jobs, delete_job
from app.schemas.job import JobCreateRequest, JobUpdateRequest
from app.core.database import get_db

job_router = APIRouter()


@job_router.delete(
    "/{uuid}",
    response_model=BaseResponse,
    status_code=200,
    summary="Delete a job by UUID",
    description="Soft deletes a job by setting its is_deleted flag to True."
)
async def delete_job_route(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(is_admin_user),
):
    try:
        result = await delete_job(uuid, db)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message=result["message"],
            payload=None,
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while deleting the job: {str(exc)}"
        )


@job_router.get(
    "/",
    response_model=BaseResponse,
    status_code=200,
    summary="Get all jobs",
    description="Retrieve a paginated list of jobs.",
)
async def get_all_jobs_route(
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of jobs per page"),
    db: AsyncSession = Depends(get_db),
):
    try:
        jobs = await load_all_jobs(db, page=page, page_size=page_size)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="Jobs retrieved successfully.",
            payload={
                "jobs": jobs,
                "page": page,
                "page_size": page_size,
            },
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving jobs: {str(exc)}",
        )


@job_router.patch(
    "/{uuid}",
    response_model=BaseResponse,
    status_code=200,
    summary="Update an existing job"
)
async def update_job_route(
        uuid: str,
        job_data: JobUpdateRequest,
        db: AsyncSession = Depends(get_db)
):
    try:
        updated_job = await update_job(uuid, db, job_data.dict(exclude_unset=True))

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Job updated successfully.",
            payload=updated_job
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=500,
            message=f"An error occurred while updating the job: {str(e)}",
            payload=None
        )


@job_router.post(
    "/",
    response_model=BaseResponse,
    status_code=201,
    summary="Create a new job",
)
async def create_job_route(
    job_data: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(is_admin_user),
):
    try:
        new_job = await create_job(db, job_data.dict())

        return BaseResponse(
            date=datetime.utcnow(),
            status=201,
            message="Job created successfully.",
            payload=new_job,
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise format_http_exception(
            status_code=500,
            message="An unexpected error occurred while creating the job.",
            details=str(e),
        )