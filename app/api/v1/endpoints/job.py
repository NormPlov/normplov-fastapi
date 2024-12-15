from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import is_admin_user
from app.exceptions.formatters import format_http_exception
from app.models import User
from app.schemas.payload import BaseResponse
from app.services.job import create_job, update_job, load_all_jobs, delete_job, load_paginated_jobs, get_job_details
from app.schemas.job import JobCreateRequest, JobUpdateRequest, PaginatedJobResponse, JobDetailsResponse
from app.core.database import get_db

job_router = APIRouter()


@job_router.get(
    "/{uuid}",
    response_model=BaseResponse,
    status_code=200,
    summary="Get job details by UUID",
    description="Retrieve detailed information for a specific job by its UUID."
)
async def get_job_details_route(
    uuid: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        job = await get_job_details(uuid, db)

        job_details = JobDetailsResponse(
            uuid=job.uuid,
            title=job.title,
            company_name=job.company,
            logo=job.logo,
            location=job.location,
            job_type=job.job_type,
            description=job.description,
            requirements=job.requirements,
            responsibilities=job.responsibilities,
            facebook_url=job.facebook_url,
            email=job.email,
            phone=job.phone,
            website=job.website,
            created_at=job.created_at,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="Job details retrieved successfully.",
            payload=job_details,
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving job details: {str(exc)}",
        )


@job_router.get(
    "/paginated-jobs",
    response_model=BaseResponse,
    status_code=200,
    summary="Get paginated jobs",
    description="Admin-only: Retrieve a paginated list of jobs based on search criteria."
)
async def get_paginated_jobs(
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of jobs per page"),
    search: Optional[str] = Query(None, description="Search term for job title or company name"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
):
    try:
        jobs, total_items = await load_paginated_jobs(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
        )

        job_list = [
            PaginatedJobResponse(
                uuid=job.uuid,
                company_logo=job.logo,
                company_name=job.company,
                province_name=job.location,
                job_category_name=job.job_category.category if job.job_category else None,
                position=job.title,
                closing_date=job.closing_date,
            )
            for job in jobs
        ]

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="Jobs retrieved successfully.",
            payload={
                "items": job_list,
                "metadata": {
                    "page": page,
                    "page_size": page_size,
                    "total_items": total_items,
                    "total_pages": (total_items + page_size - 1) // page_size,
                },
            },
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving jobs: {str(exc)}",
        )


@job_router.delete(
    "/{uuid}",
    response_model=BaseResponse,
    status_code=200,
    summary="Delete a job by UUID",
    description="Admin-only: Soft delete a job by its UUID."
)
async def delete_job_route(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
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
    description="Retrieve a searchable, sortable, and filterable list of jobs."
)
async def get_all_jobs_route(
    search: Optional[str] = Query(None, description="Search term for job title or company name"),
    sort_by: Optional[str] = Query("created_at", description="Sort by column (e.g., title, company, created_at)"),
    order: Optional[str] = Query("desc", description="Order direction ('asc' or 'desc')"),
    category: Optional[str] = Query(None, description="Filter by job category name"),
    location: Optional[str] = Query(None, description="Filter by job location"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    db: AsyncSession = Depends(get_db),
):
    try:
        jobs = await load_all_jobs(
            db=db,
            search=search,
            sort_by=sort_by,
            order=order,
            category=category,
            location=location,
            job_type=job_type,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="Jobs retrieved successfully.",
            payload={"jobs": jobs},
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