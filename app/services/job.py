import shutil
import uuid
import logging

from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import joinedload
from app.core.config import settings
from app.models import Job, JobCategory
from app.schemas.job import JobResponse, JobDetailsResponse
from datetime import datetime
from app.utils.file import validate_file_extension, validate_file_size

logger = logging.getLogger(__name__)


async def admin_load_all_jobs(
    db: AsyncSession,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    order: str = "desc"
) -> list[JobDetailsResponse]:
    try:
        stmt = select(Job).where(Job.is_deleted == False)

        if search:
            stmt = stmt.where(
                Job.title.ilike(f"%{search}%") | Job.company.ilike(f"%{search}%")
            )

        sort_column = getattr(Job, sort_by, Job.created_at)
        if order.lower() == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        stmt = stmt.options(joinedload(Job.job_category))

        result = await db.execute(stmt)
        jobs = result.scalars().all()

        return [
            JobDetailsResponse(
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
                closing_date=job.closing_date.strftime("%d.%b.%Y") if job.closing_date else None,
                job_category_name=job.job_category.name if job.job_category else None,
            )
            for job in jobs
        ]

    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while loading jobs: {str(exc)}",
        )


async def get_job_details(uuid: str, db: AsyncSession) -> Job:
    try:
        # Query to fetch job details
        stmt = select(Job).where(Job.uuid == uuid, Job.is_deleted == False)
        result = await db.execute(stmt)
        job = result.scalars().first()

        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job with UUID {uuid} not found or has been deleted."
            )

        return job

    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise Exception(f"An error occurred while fetching job details: {str(exc)}")


async def delete_job(uuid: str, db: AsyncSession) -> dict:
    try:
        stmt = select(Job).where(Job.uuid == uuid, Job.is_deleted == False)
        result = await db.execute(stmt)
        job = result.scalars().first()

        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found or already deleted."
            )

        job.is_deleted = True
        db.add(job)
        await db.commit()

        return {"message": f"Job with UUID {uuid} deleted successfully."}

    except HTTPException as exc:
        raise exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting the job: {str(exc)}"
        )


async def load_all_jobs(
    db: AsyncSession,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    order: str = "desc",
    category: Optional[str] = None,
    location: Optional[str] = None,
    job_type: Optional[str] = None
) -> list[JobDetailsResponse]:
    try:
        # Base query
        stmt = select(Job).where(Job.is_deleted == False)

        # Apply filters
        if category:
            stmt = stmt.where(Job.job_category.has(name.ilike(f"%{category}%")))
        if location:
            stmt = stmt.where(Job.location.ilike(f"%{location}%"))
        if job_type:
            stmt = stmt.where(Job.job_type.ilike(f"%{job_type}%"))

        # Search filter
        if search:
            stmt = stmt.where(
                Job.title.ilike(f"%{search}%")
                | Job.company.ilike(f"%{search}%")
                | Job.job_category.has(JobCategory.name.ilike(f"%{search}%"))
                | Job.location.ilike(f"%{search}%")
                | Job.job_type.ilike(f"%{search}%")
            )

        # Apply sorting
        sort_column = getattr(Job, sort_by, Job.created_at)
        if order.lower() == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Fetch results
        stmt = stmt.options(joinedload(Job.job_category))
        result = await db.execute(stmt)
        jobs = result.scalars().all()

        # Construct response
        return [
            JobDetailsResponse(
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
                closing_date=job.closing_date.strftime("%d.%b.%Y") if job.closing_date else None,
                job_category_name=job.job_category.name if job.job_category else None,
            )
            for job in jobs
        ]

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while loading jobs: {str(exc)}",
        )


async def update_job(uuid: uuid.UUID, db: AsyncSession, update_data: dict) -> JobResponse:
    stmt = select(Job).where(Job.uuid == uuid)
    result = await db.execute(stmt)
    job = result.scalars().first()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    for field, value in update_data.items():
        if hasattr(job, field):
            setattr(job, field, value)

    db.add(job)
    await db.commit()
    await db.refresh(job)

    job_data = {
        "uuid": str(job.uuid),
        "title": job.title,
        "company": job.company,
        "logo": job.logo,
        "facebook_url": job.facebook_url,
        "location": job.location,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "description": job.description,
        "job_type": job.job_type,
        "schedule": job.schedule,
        "salary": job.salary,
        "closing_date": job.closing_date.isoformat() if job.closing_date else None,
        "requirements": job.requirements,
        "responsibilities": job.responsibilities,
        "benefits": job.benefits,
        "email": job.email,
        "phone": job.phone,
        "website": job.website,
        "is_active": job.is_active,
    }

    return JobResponse(**job_data)


async def create_job_with_logo_service(
    title: str,
    company: str,
    location: str,
    facebook_url: Optional[str],
    posted_at: Optional[str],
    description: Optional[str],
    job_type: Optional[str],
    schedule: Optional[str],
    salary: Optional[str],
    closing_date: Optional[str],
    requirements: Optional[str],
    responsibilities: Optional[str],
    benefits: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    website: Optional[str],
    is_active: bool,
    logo: Optional[UploadFile],
    job_category_uuid: str,
    db: AsyncSession,
) -> dict:
    try:
        logo_url = None
        if logo:
            if not validate_file_extension(logo.filename):
                raise HTTPException(status_code=400, detail="Invalid file type for logo.")

            validate_file_size(logo)

            logo_directory = Path(settings.BASE_UPLOAD_FOLDER) / "job-logos"
            logo_directory.mkdir(parents=True, exist_ok=True)

            logo_path = logo_directory / f"{uuid.uuid4()}_{logo.filename}"
            with open(logo_path, "wb") as buffer:
                shutil.copyfileobj(logo.file, buffer)

            logo_url = f"{settings.BASE_UPLOAD_FOLDER}/job-logos/{logo_path.name}"

        parsed_posted_at = None
        if posted_at:
            try:
                parsed_posted_at = datetime.fromisoformat(posted_at)
                if parsed_posted_at > datetime.utcnow():
                    raise HTTPException(
                        status_code=400,
                        detail="Posted date cannot be in the future.",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid posted_at date format. Use ISO 8601 format.",
                )

        parsed_closing_date = None
        if closing_date:
            try:
                parsed_closing_date = datetime.fromisoformat(closing_date)
                if parsed_posted_at and parsed_closing_date < parsed_posted_at:
                    raise HTTPException(
                        status_code=400,
                        detail="Closing date cannot be earlier than posted date.",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid closing_date format. Use ISO 8601 format.",
                )

        job_category_id = None
        if job_category_uuid:
            stmt = select(JobCategory).where(
                JobCategory.uuid == job_category_uuid,
                JobCategory.is_deleted == False
            )
            result = await db.execute(stmt)
            job_category = result.scalars().first()
            if not job_category:
                raise HTTPException(status_code=404, detail="Job category not found.")
            job_category_id = job_category.id

        requirements_list = requirements.split(",") if requirements else None
        responsibilities_list = responsibilities.split(",") if responsibilities else None
        benefits_list = benefits.split(",") if benefits else None

        new_job = Job(
            uuid=uuid.uuid4(),
            title=title,
            company=company,
            location=location,
            facebook_url=facebook_url,
            posted_at=parsed_posted_at,
            description=description,
            job_type=job_type,
            schedule=schedule,
            salary=salary,
            closing_date=parsed_closing_date,
            requirements=requirements_list,
            responsibilities=responsibilities_list,
            benefits=benefits_list,
            email=email,
            phone=phone,
            website=website,
            is_active=is_active,
            logo=logo_url,
            job_category_id=job_category_id,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)

        return {
            "uuid": str(new_job.uuid),
        }

    except HTTPException as exc:
        raise exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating the job: {str(exc)}",
        )
