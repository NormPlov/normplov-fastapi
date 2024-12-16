import uuid
import logging

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from sqlalchemy.orm import joinedload
from app.models import Job, JobCategory
from app.schemas.job import JobResponse, JobDetailsResponse
from datetime import datetime
from sqlalchemy.exc import IntegrityError

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
        stmt = select(Job).where(Job.is_deleted == False)

        if category:
            stmt = stmt.where(Job.job_category.has(category.ilike(f"%{category}%")))
        if location:
            stmt = stmt.where(Job.location.ilike(f"%{location}%"))
        if job_type:
            stmt = stmt.where(Job.job_type.ilike(f"%{job_type}%"))

        if search:
            stmt = stmt.where(
                Job.title.ilike(f"%{search}%")
                | Job.company.ilike(f"%{search}%")
                | Job.job_category.has(Job.job_category.category.ilike(f"%{search}%"))
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


async def create_job(
    db: AsyncSession,
    job_data: dict,
) -> JobResponse:
    try:
        # Validate posted_at
        posted_at = job_data.get("posted_at")
        if posted_at:
            try:
                posted_at = datetime.fromisoformat(posted_at)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format for posted_at."
                )

        # Validate closing_date
        closing_date = job_data.get("closing_date")
        if closing_date:
            try:
                closing_date = datetime.fromisoformat(closing_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format for closing_date."
                )

        # Validate job_category_uuid
        job_category_id = None
        if job_data.get("job_category_uuid"):
            stmt = select(JobCategory).where(
                JobCategory.uuid == job_data["job_category_uuid"], JobCategory.is_deleted == False
            )
            result = await db.execute(stmt)
            job_category = result.scalars().first()
            if not job_category:
                raise HTTPException(
                    status_code=404,
                    detail="Job category not found."
                )
            job_category_id = job_category.id

        # Create the job
        new_job = Job(
            uuid=uuid.uuid4(),
            title=job_data["title"],
            company=job_data["company"],
            logo=job_data.get("logo"),
            facebook_url=job_data.get("facebook_url"),
            location=job_data.get("location"),
            posted_at=posted_at,
            description=job_data.get("description"),
            job_type=job_data.get("job_type"),
            schedule=job_data.get("schedule"),
            salary=job_data.get("salary"),
            closing_date=closing_date,
            requirements=job_data.get("requirements"),
            responsibilities=job_data.get("responsibilities"),
            benefits=job_data.get("benefits"),
            email=job_data.get("email"),
            phone=job_data.get("phone"),
            website=job_data.get("website"),
            is_active=job_data.get("is_active", True),
            is_scraped=job_data.get("is_scraped", False),
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            job_category_id=job_category_id,
        )

        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)

        return JobResponse(
            uuid=str(new_job.uuid),
            title=new_job.title,
            company=new_job.company,
            logo=new_job.logo,
            facebook_url=new_job.facebook_url,
            location=new_job.location,
            posted_at=new_job.posted_at.isoformat() if new_job.posted_at else None,
            description=new_job.description,
            job_type=new_job.job_type,
            schedule=new_job.schedule,
            salary=new_job.salary,
            closing_date=new_job.closing_date.isoformat() if new_job.closing_date else None,
            requirements=new_job.requirements,
            responsibilities=new_job.responsibilities,
            benefits=new_job.benefits,
            email=new_job.email,
            phone=new_job.phone,
            website=new_job.website,
            is_active=new_job.is_active,
            created_at=new_job.created_at.isoformat(),
            updated_at=new_job.updated_at.isoformat() if new_job.updated_at else None,
            job_category_uuid=str(job_data.get("job_category_uuid")),
        )

    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Integrity error: {str(e)}"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating the job: {str(e)}"
        )
