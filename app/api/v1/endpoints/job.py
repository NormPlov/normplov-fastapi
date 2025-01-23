import logging
import uuid as uuid_lib
import re

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import is_admin_user
from app.exceptions.formatters import format_http_exception
from app.models import User
from app.schemas.payload import BaseResponse
from app.schemas.job import JobDetailsResponse, JobCreateRequest, JobUpdateRequest
from app.core.database import get_db
from app.utils.pagination import paginate_results
from app.services.job import (
    load_all_jobs,
    delete_job,
    admin_load_all_jobs,
    update_job,
    get_unique_job_categories,
    get_trending_jobs, fetch_job_details, increment_visitor_count, create_job_service
)

job_router = APIRouter()
logger = logging.getLogger(__name__)


@job_router.get(
    "/trending-jobs",
    response_model=BaseResponse,
    status_code=200,
    summary="Get trending job data for graph",
    description="Fetch trending job data grouped by month based on job category."
)
async def get_trending_jobs_data_route(db: AsyncSession = Depends(get_db)):
    try:
        trending_data = await get_trending_jobs(db)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="Trending job data retrieved successfully.",
            payload=trending_data,
        )

    except ValueError as exc:
        raise format_http_exception(
            status_code=400,
            message="❌ Invalid request for trending job data.",
            details={"error_message": str(exc)}
        )
    except SQLAlchemyError as exc:
        raise format_http_exception(
            status_code=400,
            message="🛠️ Database error occurred while fetching trending job data.",
            details={"error_message": str(exc)}
        )
    except Exception as exc:
        raise format_http_exception(
            status_code=400,
            message="😿 Could not fetch trending job data.",
            details={"error_message": str(exc)}
        )


@job_router.get(
    "/categories",
    response_model=BaseResponse,
    status_code=200,
    summary="Get unique job categories",
    description="Retrieve a list of unique job categories."
)
async def get_job_categories_route(db: AsyncSession = Depends(get_db)):
    try:
        # Fetch unique categories
        raw_categories = await get_unique_job_categories(db)

        # Clean the categories
        categories = [
            re.sub(r'[\\/"]+', '', category).strip() for category in raw_categories if category
        ]

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="Job categories retrieved successfully.",
            payload={"categories": categories},
        )

    except ValueError as exc:
        raise format_http_exception(
            status_code=400,
            message="❌ Invalid data encountered while fetching job categories.",
            details={"error_message": str(exc)}
        )
    except SQLAlchemyError as exc:
        raise format_http_exception(
            status_code=400,
            message="🛠️ Database error occurred while fetching job categories.",
            details={"error_message": str(exc)}
        )
    except Exception as exc:
        raise format_http_exception(
            status_code=400,
            message="😿 Could not retrieve job categories.",
            details={"error_message": str(exc)}
        )


@job_router.get(
    "/admin/all-jobs",
    response_model=BaseResponse,
    status_code=200,
    summary="Admin: Get all jobs",
    description="Retrieve all jobs with detailed information for admin users."
)
async def admin_get_all_jobs_route(
    search: Optional[str] = Query(None, description="Search term for job title or company name"),
    sort_by: Optional[str] = Query("created_at", description="Sort by column (e.g., title, company, created_at)"),
    order: Optional[str] = Query("desc", description="Order direction ('asc' or 'desc')"),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of jobs per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
):
    try:
        jobs = await admin_load_all_jobs(
            db=db,
            search=search,
            sort_by=sort_by,
            order=order,
        )

        paginated_result = paginate_results(jobs, page=page, page_size=page_size)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="✅ Jobs retrieved successfully.",
            payload=paginated_result,
        )

    except ValueError as exc:
        raise format_http_exception(
            status_code=400,
            message="⚙️ Invalid request parameters.",
            details={"error_message": str(exc)}
        )
    except SQLAlchemyError as exc:
        raise format_http_exception(
            status_code=400,
            message="❌ Database error occurred while retrieving jobs.",
            details={"error_message": str(exc)}
        )
    except Exception as exc:
        raise format_http_exception(
            status_code=400,
            message="😥 Could not retrieve jobs.",
            details={"error_message": str(exc)}
        )


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
        try:
            uuid_obj = uuid_lib.UUID(uuid, version=4)
        except ValueError:
            raise format_http_exception(
                status_code=400,
                message="😿 Invalid UUID format.",
                details={"provided_uuid": uuid}
            )

        job = await fetch_job_details(uuid, db)

        await increment_visitor_count(job, db)

        job_details = JobDetailsResponse(
            uuid=job.uuid,
            title=job.title,
            company_name=job.company,
            logo=job.logo,
            posted_at=job.posted_at,
            schedule=job.schedule,
            salary=job.salary,
            location=job.location,
            job_type=job.job_type,
            description=job.description,
            requirements=job.requirements,
            responsibilities=job.responsibilities,
            benefits=job.benefits,
            facebook_url=job.facebook_url,
            email=job.email,
            phone=job.phone,
            website=job.website,
            closing_date=job.closing_date.strftime("%d.%b.%Y") if job.closing_date else None,
            category=job.category,
            created_at=job.created_at,
            is_scraped=job.is_scraped
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="✅ Job details retrieved successfully.",
            payload=job_details,
        )

    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise format_http_exception(
            status_code=400,
            message="😥 Could not retrieve job details.",
            details={"error_message": str(exc)}
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

    except ValueError as exc:
        raise format_http_exception(
            status_code=400,
            message="❌ Invalid UUID format.",
            details={"provided_uuid": uuid, "error_message": str(exc)}
        )
    except SQLAlchemyError as exc:
        raise format_http_exception(
            status_code=400,
            message="🛠️ Database error occurred while deleting the job.",
            details={"error_message": "An issue occurred while querying the database."}
        )
    except Exception as exc:
        logger.error(f"Unexpected error while deleting job: {str(exc)}")
        raise format_http_exception(
            status_code=400,
            message="😿 Could not delete the job.",
            details={"error_message": str(exc)}
        )


@job_router.get(
    "",
    response_model=BaseResponse,
    status_code=200,
    summary="Get all jobs",
    description="Retrieve a searchable, sortable, and filterable list of jobs with pagination."
)
async def get_all_jobs_route(
    search: Optional[str] = Query(None, description="Search term for job title, company name, or location"),
    sort_by: Optional[str] = Query("created_at", description="Sort by column (e.g., title, company, created_at)"),
    order: Optional[str] = Query("desc", description="Order direction ('asc' or 'desc')"),
    location: Optional[str] = Query(None, description="Filter by job location"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    category: Optional[str] = Query(None, description="Filter by job category"),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of jobs per page"),
    db: AsyncSession = Depends(get_db),
):
    try:
        # Load jobs
        jobs = await load_all_jobs(
            db=db,
            search=search,
            sort_by=sort_by,
            order=order,
            location=location,
            job_type=job_type,
            category=category,
        )

        # Paginate results
        paginated_result = paginate_results(jobs, page=page, page_size=page_size)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="✅ Jobs retrieved successfully.",
            payload=paginated_result,
        )

    except Exception as e:
        raise format_http_exception(
            status_code=400,
            message="😿 Could not retrieve the job.",
            details={"error_message": str(e)}
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
    db: AsyncSession = Depends(get_db),
):
    try:
        update_data = job_data.dict(exclude_unset=True)

        updated_job = await update_job(uuid, db, update_data)

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="✅ Job updated successfully.",
            payload=updated_job.dict()
        )

    except ValueError as e:
        raise format_http_exception(
            status_code=400,
            message="❌ Invalid data provided for updating the job.",
            details={"error_message": str(e)}
        )
    except SQLAlchemyError as e:
        raise format_http_exception(
            status_code=400,
            message="🛠️ Database error occurred while updating the job.",
            details={"error_message": str(e)}
        )
    except Exception as e:
        raise format_http_exception(
            status_code=400,
            message="😿 Could not update the job.",
            details={"error_message": str(e)}
        )


@job_router.post(
    "",
    response_model=BaseResponse,
    status_code=201,
    summary="Create a new job with a logo",
)
async def create_job_route(
    job_data: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(is_admin_user),
):
    try:
        job_response = await create_job_service(
            title=job_data.title,
            company=job_data.company,
            location=job_data.location,
            facebook_url=job_data.facebook_url,
            posted_at=job_data.posted_at,
            description=job_data.description,
            job_type=job_data.job_type,
            schedule=job_data.schedule,
            salary=job_data.salary,
            closing_date=job_data.closing_date,
            requirements=job_data.requirements,
            responsibilities=job_data.responsibilities,
            benefits=job_data.benefits,
            email=job_data.email,
            phone=job_data.phone,
            website=job_data.website,
            is_active=job_data.is_active,
            logo=job_data.logo,
            category=job_data.category,
            db=db,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=201,
            message="✅ Job created successfully.",
            payload=job_response,
        )

    except ValueError as e:
        raise format_http_exception(
            status_code=400,
            message="❌ Invalid job data provided.",
            details={"error_message": str(e)}
        )
    except SQLAlchemyError as e:
        raise format_http_exception(
            status_code=400,
            message="🛠️ Database error occurred while creating the job.",
            details={"error_message": str(e)}
        )
    except Exception as e:
        raise format_http_exception(
            status_code=400,
            message="😿 Could not create the job.",
            details={"error_message": str(e)}
        )