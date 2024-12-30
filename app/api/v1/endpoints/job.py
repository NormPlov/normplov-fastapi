import logging
import uuid as uuid_lib
import re

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import is_admin_user
from app.models import User
from app.schemas.payload import BaseResponse
from app.schemas.job import JobDetailsResponse
from app.core.database import get_db
from app.utils.pagination import paginate_results
from app.services.job import (
    load_all_jobs,
    delete_job,
    get_job_details,
    admin_load_all_jobs,
    create_job, update_job,
    get_unique_job_categories,
    get_trending_jobs
)

job_router = APIRouter()
logger = logging.getLogger(__name__)


@job_router.get(
    "/trending-jobs",
    response_model=BaseResponse,
    status_code=200,
    summary="Get trending job data for graph",
    description="Fetch trending job data grouped by month based on job title."
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
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching trending job data: {str(exc)}",
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
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while fetching job categories: {str(exc)}"
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
            message="Jobs retrieved successfully.",
            payload=paginated_result,
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(exc)}",
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
            raise HTTPException(status_code=400, detail="Invalid UUID format.")

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
            closing_date=job.closing_date.strftime("%d.%b.%Y") if job.closing_date else None,
            category=job.category,
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
    category: Optional[str] = Query(None, description="Filter by job category"),  # New filter parameter
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of jobs per page"),
    db: AsyncSession = Depends(get_db),
):
    try:
        jobs = await load_all_jobs(
            db=db,
            search=search,
            sort_by=sort_by,
            order=order,
            location=location,
            job_type=job_type,
            category=category,
        )

        paginated_result = paginate_results(jobs, page=page, page_size=page_size)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="Jobs retrieved successfully.",
            payload=paginated_result,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(exc)}",
        )


@job_router.patch(
    "/{uuid}",
    response_model=BaseResponse,
    status_code=200,
    summary="Update an existing job"
)
async def update_job_route(
    uuid: str,
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    company: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    facebook_url: Optional[str] = Form(None),
    posted_at: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    job_type: Optional[str] = Form(None),
    schedule: Optional[str] = Form(None),
    salary: Optional[str] = Form(None),
    closing_date: Optional[str] = Form(None),
    requirements: Optional[str] = Form(None),
    responsibilities: Optional[str] = Form(None),
    benefits: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    logo: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        update_data = {
            "title": title,
            "category": category,
            "company": company,
            "location": location,
            "facebook_url": facebook_url,
            "posted_at": posted_at,
            "description": description,
            "job_type": job_type,
            "schedule": schedule,
            "salary": salary,
            "closing_date": closing_date,
            "requirements": requirements,
            "responsibilities": responsibilities,
            "benefits": benefits,
            "email": email,
            "phone": phone,
            "website": website,
            "logo": logo,
        }

        update_data = {key: value for key, value in update_data.items() if value is not None}

        updated_job = await update_job(uuid, db, update_data)

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Job updated successfully.",
            payload=updated_job.dict()
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while updating the job: {str(e)}"
        )


@job_router.post(
    "",
    response_model=BaseResponse,
    status_code=201,
    summary="Create a new job with a logo",
)
async def create_job_route(
    title: str = Form(None),
    company: str = Form(None),
    location: str = Form(None),
    facebook_url: str = Form(None),
    posted_at: str = Form(None),
    description: str = Form(None),
    job_type: str = Form(None),
    schedule: str = Form(None),
    salary: str = Form(None),
    closing_date: str = Form(None),
    requirements: str = Form(None),
    responsibilities: str = Form(None),
    benefits: str = Form(None),
    email: str = Form(None),
    phone: str = Form(None),
    website: str = Form(None),
    is_active: bool = Form(True),
    logo: str = Form(None),
    category: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(is_admin_user),
):
    try:
        job_response = await create_job(
            title=title,
            company=company,
            location=location,
            facebook_url=facebook_url,
            posted_at=posted_at,
            description=description,
            job_type=job_type,
            schedule=schedule,
            salary=salary,
            closing_date=closing_date,
            requirements=requirements,
            responsibilities=responsibilities,
            benefits=benefits,
            email=email,
            phone=phone,
            website=website,
            is_active=is_active,
            logo=logo,
            category=category,
            db=db,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=201,
            message="Job created successfully.",
            payload=job_response,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while creating the job: {str(e)}",
        )
