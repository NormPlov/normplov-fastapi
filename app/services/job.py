import shutil
import uuid
import logging

from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, or_
from fastapi import HTTPException, UploadFile
from app.core.config import settings
from app.models import Job
from app.schemas.job import JobDetailsResponse, JobResponse
from datetime import datetime
from app.utils.file import validate_file_extension, validate_file_size
from sqlalchemy import and_

logger = logging.getLogger(__name__)


async def get_trending_jobs(db: AsyncSession) -> dict:
    try:
        title_query = text("""
            SELECT 
                date_trunc('month', jobs.posted_at) AS month,
                jobs.title AS label,
                COUNT(jobs.id) AS count
            FROM jobs
            WHERE jobs.is_deleted = false 
              AND jobs.posted_at IS NOT NULL
            GROUP BY date_trunc('month', jobs.posted_at), jobs.title
            ORDER BY date_trunc('month', jobs.posted_at) ASC, COUNT(jobs.id) DESC
        """)

        title_result = await db.execute(title_query)
        title_data = title_result.fetchall()

        all_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        trending_jobs = {month: {"month": month, "label": "", "count": 0} for month in all_months}

        for row in title_data:
            month = row.month.strftime("%b")
            label = row.label.strip()
            count = row.count

            if count > trending_jobs[month]["count"]:
                trending_jobs[month]["label"] = label
                trending_jobs[month]["count"] = count

        trending_jobs_list = list(trending_jobs.values())

        return {"trending_jobs": trending_jobs_list}

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching trending job data: {str(exc)}",
        )


async def get_unique_job_categories(db: AsyncSession) -> list[str]:
    try:
        stmt = select(Job.category).where(Job.is_deleted == False, Job.category.isnot(None)).distinct()
        result = await db.execute(stmt)
        categories = result.scalars().all()
        return categories
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving job categories: {str(exc)}"
        )


async def admin_load_all_jobs(
    db: AsyncSession,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    order: str = "desc"
) -> list[JobDetailsResponse]:
    try:
        current_datetime = datetime.utcnow()

        stmt = select(Job).where(
            and_(
                Job.is_deleted == False,
                or_(
                    Job.closing_date.is_(None),
                    Job.closing_date >= current_datetime
                )
            )
        )

        if search:
            stmt = stmt.where(
                Job.title.ilike(f"%{search}%") | Job.company.ilike(f"%{search}%")
            )

        sort_column = getattr(Job, sort_by, Job.created_at)
        if order.lower() == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        result = await db.execute(stmt)
        jobs = result.scalars().all()

        return [
            JobDetailsResponse(
                uuid=job.uuid,
                title=job.title if job.title else "Unknown Title",
                company_name=job.company if job.company else "Unknown Company",
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
                category=job.category if job.category else None,
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
    location: Optional[str] = None,
    job_type: Optional[str] = None,
    category: Optional[str] = None,
) -> list[JobDetailsResponse]:
    try:
        stmt = select(Job).where(Job.is_deleted == False)

        if location:
            stmt = stmt.where(Job.location.ilike(f"%{location}%"))
        if job_type:
            stmt = stmt.where(Job.job_type.ilike(f"%{job_type}%"))
        if category:
            stmt = stmt.where(Job.category.ilike(f"%{category}%"))

        if search:
            stmt = stmt.where(
                Job.title.ilike(f"%{search}%")
                | Job.company.ilike(f"%{search}%")
                | Job.location.ilike(f"%{search}%")
                | Job.job_type.ilike(f"%{search}%")
            )

        sort_column = getattr(Job, sort_by, Job.created_at)
        if order.lower() == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        result = await db.execute(stmt)
        jobs = result.scalars().all()

        return [
            JobDetailsResponse(
                uuid=job.uuid,
                title=job.title if job.title else "Unknown Title",
                company_name=job.company if job.company else "Unknown Company",
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
                closing_date=job.closing_date.strftime("%d.%b.%Y") if job.closing_date and job.closing_date >= datetime.utcnow() else None,
                category=job.category,
            )
            for job in jobs
            if job.closing_date is None or job.closing_date >= datetime.utcnow()
        ]

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while loading jobs: {str(exc)}",
        )


async def update_job(
    job_uuid: str,
    db: AsyncSession,
    update_data: dict,
    logo: Optional[UploadFile] = None,
) -> JobResponse:
    try:
        stmt = select(Job).where(Job.uuid == job_uuid, Job.is_deleted == False)
        result = await db.execute(stmt)
        job = result.scalars().first()

        if not job:
            raise HTTPException(
                status_code=404, detail="Job not found or has been deleted."
            )

        if "closing_date" in update_data:
            try:
                closing_date = datetime.fromisoformat(update_data["closing_date"])
                if closing_date < datetime.utcnow():
                    update_data["is_active"] = False
                update_data["closing_date"] = closing_date
            except ValueError:
                raise HTTPException(400, detail="Invalid date format for closing_date.")

        if "posted_at" in update_data:
            try:
                posted_at = datetime.fromisoformat(update_data["posted_at"])
                if posted_at > datetime.utcnow():
                    raise HTTPException(400, detail="Posted date cannot be in the future.")
                update_data["posted_at"] = posted_at
            except ValueError:
                raise HTTPException(400, detail="Invalid date format for posted_at.")

        # Handle logo updates
        if logo:
            if not validate_file_extension(logo.filename):
                raise HTTPException(status_code=400, detail="Invalid file type for logo.")
            validate_file_size(logo)

            logo_directory = Path(settings.BASE_UPLOAD_FOLDER) / "job-logos"
            logo_directory.mkdir(parents=True, exist_ok=True)

            logo_path = logo_directory / f"{job_uuid}_{uuid.uuid4()}_{logo.filename}"
            with open(logo_path, "wb") as buffer:
                shutil.copyfileobj(logo.file, buffer)

            update_data["logo"] = f"{settings.BASE_UPLOAD_FOLDER}/job-logos/{logo_path.name}"

        # Apply updates
        for field, value in update_data.items():
            if hasattr(job, field):
                setattr(job, field, value)

        db.add(job)
        await db.commit()
        await db.refresh(job)

        return JobResponse(
            uuid=str(job.uuid),
            title=job.title,
            category=job.category,
            company=job.company,
            logo=job.logo,
            facebook_url=job.facebook_url,
            location=job.location,
            posted_at=job.posted_at.isoformat() if job.posted_at else None,
            description=job.description,
            job_type=job.job_type,
            schedule=job.schedule,
            salary=job.salary,
            closing_date=job.closing_date.isoformat() if job.closing_date else None,
            requirements=job.requirements,
            responsibilities=job.responsibilities,
            benefits=job.benefits,
            email=job.email,
            phone=job.phone,
            website=job.website,
        )
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while updating the job: {exc}"
        )


async def create_job(
    title: Optional[str],
    company: Optional[str],
    location: Optional[str],
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
    category: Optional[str],
    db: AsyncSession,
) -> dict:
    try:
        parsed_posted_at = None
        if posted_at:
            parsed_posted_at = datetime.fromisoformat(posted_at)
            if parsed_posted_at > datetime.utcnow():
                raise HTTPException(status_code=400, detail="Posted date cannot be in the future.")

        parsed_closing_date = None
        if closing_date:
            parsed_closing_date = datetime.fromisoformat(closing_date)
            if parsed_closing_date < datetime.utcnow():
                is_active = False

        requirements_list = requirements.split(",") if requirements else None
        responsibilities_list = responsibilities.split(",") if responsibilities else None
        benefits_list = benefits.split(",") if benefits else None

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
            category=category,
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
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating the job: {str(exc)}",
        )
